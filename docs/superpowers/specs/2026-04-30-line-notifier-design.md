# LINE通知基盤（LineNotifier）設計

## Goal

KabuSys に LINE 通知をアドオンとして追加する。通知はシステムの中核ロジックと疎結合にし、設定ファイルで有効/無効を切り替えられるようにする。

## 背景

- `monitoring/alert_manager.py` は既に LINE Messaging API で障害アラートを実装済み
- 定期通知（日次・週次・月次レポートの送信）は未実装
- ドキュメントに残る Slack/Email 記述を LINE に統一する

## スコープ

### 今回実装するもの

- `src/kabusys/operations/notifier.py`: `LineNotifier` クラスと `build_notifier()` ファクトリ
- `src/kabusys/config.py`: `LINE_NOTIFY_ENABLED` プロパティの追加
- `tests/test_notifier.py`: `LineNotifier` の単体テスト
- ドキュメント更新: Slack/Email 記述を LINE に書き換え

### 今回スコープ外

- 既存バッチスクリプトへの `notifier.send()` 組み込み（別 Issue）
- 定期通知のスケジューリング（別 Issue）

---

## アーキテクチャ

```
Settings (.env)
  LINE_CHANNEL_ACCESS_TOKEN=xxx   # 既存
  LINE_USER_ID=xxx                # 既存
  LINE_NOTIFY_ENABLED=true        # 新規追加（省略時 true）

operations/notifier.py
  LineNotifier
    .send(message: str) -> bool

  build_notifier(settings: Settings) -> LineNotifier

呼び出し元（将来）
  run_night_batch.py ─┐
  run_execution.py   ─┼→ notifier.send(report_markdown)
  run_monitoring.py  ─┘
```

**責務の分担:**

- `LineNotifier`: LINE API への送信のみ。メッセージ内容は関知しない
- 既存レポートモジュール（`market_close_report.py` 等）: 内容生成は従来通り
- 呼び出し元スクリプト: 生成した内容を `notifier.send()` に渡すかどうかを判断

`alert_manager.py`（障害アラート・クールダウン付き）と `notifier.py`（定期送信・シンプル）は共存する。用途が異なるため統合しない。

---

## Settings 仕様

`src/kabusys/config.py` の `Settings` クラスに以下を追加する。

```python
@property
def line_notify_enabled(self) -> bool:
    return os.environ.get("LINE_NOTIFY_ENABLED", "true").lower() not in ("false", "0", "no")
```

既存プロパティ:

```python
@property
def line_channel_access_token(self) -> str:
    return os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

@property
def line_user_id(self) -> str:
    return os.environ.get("LINE_USER_ID", "")
```

`.env` 設定例:

```env
LINE_CHANNEL_ACCESS_TOKEN=your_token_here
LINE_USER_ID=Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LINE_NOTIFY_ENABLED=true
```

未設定時のデフォルト:
- `LINE_CHANNEL_ACCESS_TOKEN`: 空文字（通知無効と同義）
- `LINE_USER_ID`: 空文字（通知無効と同義）
- `LINE_NOTIFY_ENABLED`: `true`

---

## LineNotifier 仕様

### クラスシグネチャ

```python
class LineNotifier:
    def __init__(
        self,
        token: str,
        user_id: str,
        enabled: bool = True,
    ) -> None: ...

    def send(self, message: str) -> bool:
        """LINE push message を送信する。

        Returns:
            True: 送信成功
            False: スキップ（無効/未設定/エラー）
        """
```

### 送信ロジック

1. `enabled=False` または `token` / `user_id` が空文字 → ログのみ、`False` を返す
2. `message` が 5,000 文字を超える場合、末尾を切り詰めて `...(省略)` を付加
3. LINE Messaging API (`https://api.line.me/v2/bot/message/push`) に POST
4. ステータス 2xx → `True` を返す
5. ステータス 2xx 以外または接続エラー → `logger.error` を呼び、`False` を返す

### ファクトリ関数

```python
def build_notifier(settings: Settings) -> LineNotifier:
    """Settings から LineNotifier を生成する。"""
    return LineNotifier(
        token=settings.line_channel_access_token,
        user_id=settings.line_user_id,
        enabled=settings.line_notify_enabled,
    )
```

---

## テスト仕様

`tests/test_notifier.py` に以下のテストを実装する。`requests.post` をモックして HTTP は叩かない。

| テスト名 | 検証内容 |
|---|---|
| `test_send_disabled_returns_false` | `enabled=False` → `False`、API 未呼び出し |
| `test_send_no_token_returns_false` | `token=""` → `False`、API 未呼び出し |
| `test_send_no_user_id_returns_false` | `user_id=""` → `False`、API 未呼び出し |
| `test_send_success` | 正常送信 → `True`、ペイロード検証 |
| `test_send_api_error_returns_false` | 4xx/5xx → `False` |
| `test_send_request_exception_returns_false` | 接続エラー → `False` |
| `test_send_truncates_long_message` | 5,000 文字超 → 切り詰めて送信 |
| `test_build_notifier_from_settings` | `build_notifier()` が Settings から正しく構築される |

---

## ドキュメント更新対象

以下のファイルから Slack/Email 記述を削除または LINE Messaging API に書き換える。

| ファイル | 対応内容 |
|---|---|
| `documents/08_Operations/Monitoring.md` | `Slack` → `LINE Messaging API` |
| `documents/10_Runtime/RuntimeArchitecture.md` | `Slack通知` → `LINE通知` |
| `documents/00_Architecture/InterfaceSpec.md` | `Slack通知` → `LINE通知` |
| `documents/00_Architecture/ImplementationRoadmap.md` | Slack/Email 記述を確認して更新 |
| その他（4ファイル） | 記述がなければスキップ |
