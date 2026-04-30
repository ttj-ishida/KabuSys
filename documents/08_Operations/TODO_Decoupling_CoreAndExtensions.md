# TODO: Core機能と拡張機能（AI/LINE/UI）の疎結合化

本ドキュメントは、KabuSysにおいて「拡張機能（AIセンチメント、LINE通知、運用UI）が停止・未設定であっても、Core機能（自動売買）が絶対に影響を受けないアーキテクチャ」を実現するための、具体的なファイルごとの改修タスクリストです。

## 1. Feature Toggle（機能フラグ）の導入
システム全体で拡張機能のON/OFFを一元管理できるようにします。

- [ ] `src/kabusys/config.py` の修正
  - `.env` から以下のフラグを読み込む設定を追加する
    - `ENABLE_AI_SENTIMENT` (bool, デフォルト `False`)
    - `ENABLE_LINE_NOTIFY` (bool, デフォルト `False`)
- [ ] `.env.example` の修正
  - ユーザーが任意機能を利用するかどうかを選択できるよう、上記フラグのサンプルを追記する

## 2. AIモジュールのフェイルセーフ（欠損値へのフォールバック）
AI機能がOFF、またはOpenAI APIキーが未設定の場合でも、システムがクラッシュせずにルールベースのみで動作するようにします。

- [ ] `src/kabusys/ai/news_nlp.py` の修正
  - 処理の冒頭で `if not config.ENABLE_AI_SENTIMENT:` をチェックし、`False` の場合は「AIによるセンチメント分析をスキップします」とログを出力して即座に `return` するように改修。
- [ ] `src/kabusys/strategy/signal_generator.py` の確認・強化
  - 現在の実装（`s_news if s_news is not None else 0.5`）が正常に機能しているかをテストコードで保護する。
  - AIスコアが欠損（`None`）だった場合、「WARNING: AIスコアが見つかりません。デフォルト値(0.5)でシグナルを生成します」というログを出すようにして、運用者が状況を把握しやすくする。

## 3. LINE通知の疎結合化（イベント駆動への変更）
発注処理モジュールがLINE APIと直接通信（密結合）しないように分離し、LINE APIの障害が発注の失敗につながるリスクを排除します。

- [ ] `src/kabusys/run_execution.py`（または `execution` 配下の該当モジュール）の修正
  - 約定や発注成功時、直接 `send_line_message()` などを呼ぶコードを削除。
  - 代わりに、SQLiteデータベースの `notification_events` テーブルに「発注完了」というステータスを `INSERT` するだけの処理に変更（または `logging` ベースのイベント記録）。
- [ ] 新規作成: `src/kabusys/operations/notifier_worker.py`（通知専用ワーカー）
  - 定期的に `notification_events` テーブル（またはログ）を監視し、未送信の通知があればLINEに送信する独立したバッチスクリプトを作成する。
  - このスクリプトは `if config.ENABLE_LINE_NOTIFY:` が `True` の場合のみ起動するようにする。

## 4. UI設定ファイルのRead-Only制約と安全な初期値
Streamlitダッシュボードが一度も起動されず、外部設定ファイルが作成されていない状態でも、システムが安全にデフォルト値で起動できるようにします。

- [ ] `src/kabusys/strategy/signal_generator.py`（または関連モジュール）の修正
  - `strategy_config.json` を読み込む際、`try...except FileNotFoundError:` で囲む。
  - ファイルが見つからない場合はエラーで終了するのではなく、安全な初期値（`DEFAULT_STRATEGY_PARAMS` 等）を自動で適用し、「INFO: 設定ファイルがないため、デフォルトの安全パラメータで動作します」とログを出力して処理を継続させる。
