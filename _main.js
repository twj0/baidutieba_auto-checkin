// tieba_final_test.js
import { createHash } from 'crypto';

const CONFIG = {
    BDUSS: "1N5NGpncnJHQWgwcGpMeWs3bnpyUHJNNGFpZEJVVTZWenQ2MVBOWFdkR0Q5SVZvSVFBQUFBJCQAAAAAAQAAAAEAAABc2iB45-Ln4ufiMTE0NTE0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAINnXmiDZ15oM",
};

const LIKIE_URL = "http://c.tieba.baidu.com/c/f/forum/like";
const SIGN_KEY = 'tiebaclient!!!';
const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36';

function md5(str) { return createHash('md5').update(str).digest('hex'); }
function encodeData(params) {
    const sortedKeys = Object.keys(params).sort();
    const str = sortedKeys.map(key => `${key}=${params[key]}`).join('') + SIGN_KEY;
    params.sign = md5(str).toUpperCase();
    return new URLSearchParams(params);
}

async function finalTest() {
    console.log("--- 终极调试脚本启动 ---");

    const params = {
        'BDUSS': CONFIG.BDUSS,
        '_client_type': '2',
        '_client_id': 'wappc_1534235498291_488',
        '_client_version': '9.7.8.0',
        '_phone_imei': '000000000000000',
        'from': '1008621y',
        'page_no': '1',
        'page_size': '200',
        'model': 'MI+5',
        'net_type': '1',
        'timestamp': String(Math.floor(Date.now() / 1000)),
        'vcode_tag': '11',
    };
    const signedParams = encodeData(params);

    try {
        console.log("\n1. 正在发送请求...");
        const response = await fetch(LIKIE_URL, { method: 'POST', headers: { 'User-Agent': USER_AGENT, 'Content-Type': 'application/x-www-form-urlencoded' }, body: signedParams });
        
        if (!response.ok) {
            throw new Error(`API 请求失败，状态码: ${response.status}`);
        }
        
        const rawText = await response.text();
        console.log("2. 成功接收到响应！原始文本 (前500字符):");
        console.log("--------------------------------------------------");
        console.log(rawText.substring(0, 500) + "...");
        console.log("--------------------------------------------------\n");

        console.log("3. 正在将原始文本解析为 JSON...");
        const data = JSON.parse(rawText);
        console.log("   ✅ 解析成功！\n");

        console.log("4. 正在深入分析解析后的数据结构...");
        const forumList = data.forum_list;
        if (!forumList) {
            console.log("   ❌ 错误: 解析后的对象中不存在 'forum_list' 键！");
            return;
        }

        const nonGconforum = forumList.non_gconforum;
        if (!nonGconforum) {
            console.log("   ❌ 错误: 'forum_list' 对象中不存在 'non_gconforum' 键！");
            console.log("   'forum_list' 包含的键:", Object.keys(forumList));
            return;
        }

        console.log(`   - 'non_gconforum' 的类型是: ${typeof nonGconforum}`);
        console.log(`   - 'non_gconforum' 是不是一个数组? ${Array.isArray(nonGconforum)}`);
        console.log(`   - 'non_gconforum' 的长度是: ${nonGconforum.length}\n`);
        
        if (nonGconforum.length > 0) {
            console.log("5. ✅ 探测成功！Node.js 确认 'non_gconforum' 是一个包含内容的数组！");
            console.log("   第一个贴吧的名称是:", nonGconforum[0].name);
        } else {
             console.log("5. ❌ 探测失败！Node.js 认为 'non_gconforum' 是一个空数组或无法识别长度！");
        }

        console.log("\n6. 完整数据结构透视 (console.dir):");
        console.dir(data, { depth: 5 }); // 打印对象的详细结构

    } catch (error) {
        console.error(`\n[FATAL] 脚本执行过程中发生严重错误: ${error.message}`);
    }
}

main();