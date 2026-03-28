# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティック バージョニングを採用しています。

- 未リリースの変更は [Unreleased] に記載します。
- 既リリースの項目はバージョンごとに日付とともに記載します。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-28

初回リリース。日本株のデータ収集、特徴量計算、AIベースのニュース/レジーム評価、および運用ユーティリティを含む自動売買・リサーチ基盤を提供します。

### 追加 (Added)
- パッケージ全体
  - 基本パッケージ定義とバージョン: kabusys v0.1.0 を追加。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env / .env.local の読み込み順序（OS環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env のパースロジックを実装（export 句、シングル/ダブルクォート、エスケープ、インラインコメント処理を含む）。
  - Settings クラスを提供し、主要設定プロパティをラップ：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須取得。
    - KABUSYS_ENV（development, paper_trading, live の検証）と LOG_LEVEL（DEBUG/INFO/... の検証）。
    - デフォルト DB パス（DUCKDB_PATH / SQLITE_PATH）の展開メソッド。
    - is_live / is_paper / is_dev のブールプロパティ。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ保存。
    - チャンク処理（最大 20 銘柄/コール）、記事トリム（記事数・文字数上限）を実装。
    - JSON Mode のレスポンス検証ロジック（厳密な構造検査、部分的な前後テキスト回復、スコアのクリップ）を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフを実装。
    - API 呼び出しをテストの差し替え可能にする _call_openai_api フックを用意。
    - calc_news_window: JSTベースのニュース収集ウィンドウ計算を提供（前日15:00～当日08:30 JST）。

  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（ルックアヘッド回避のため target_date 未満データのみ使用）、マクロ記事フィルタ（キーワード群）取得、OpenAI 呼び出しと JSON パースを実装。
    - 失敗時のフェイルセーフ（API 失敗やパース失敗は macro_sentiment=0.0）とリトライロジックを備える。
    - 結果は market_regime テーブルに冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）される。
    - テスト容易性のため _call_openai_api を差し替え可能。

- データ / ETL / カレンダー (src/kabusys/data)
  - ETL パイプライン用の ETLResult（pipeline.ETLResult を etl モジュールで再公開）。
  - pipeline.py: 差分取得、バックフィル、品質チェック（quality モジュール利用）の設計に基づくユーティリティとヘルパーを追加。DuckDB の最大日付取得やテーブル存在チェック等を実装。
  - calendar_management.py:
    - JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API を提供。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 優先ルール、最大探索日数による保護を実装。
    - J-Quants クライアント (jquants_client) を利用した取得・保存機能呼び出しポイントを用意。

- リサーチ機能 (src/kabusys/research)
  - factor_research.py:
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、ATR 比率、出来高流動性指標）、Value（PER、ROE）等のファクター計算を実装。
    - DuckDB を用いた SQL ベースの実装、データ不足時の None 処理、結果を辞書のリストで返す API。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: スピアマンランク相関）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を提供。
    - Pandas 等外部依存を使わず標準ライブラリで実装。

### 変更 (Changed)
- （初回リリースのため履歴なし）

### 修正 (Fixed)
- （初回リリースのため履歴なし）

### セキュリティ (Security)
- 必須 API キー（OpenAI 等）未設定時に ValueError を送出し明示的に通知する仕組みを導入。  
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を要求。

### 既知の設計上の注意点 / 動作仕様
- ルックアヘッドバイアス防止:
  - AI スコア/レジーム算出/ファクター計算は datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を指定する設計。
  - DB クエリは target_date を境に過去データのみを参照するよう実装されている。
- OpenAI 呼び出し:
  - gpt-4o-mini を前提に JSON mode を利用。API レスポンスの堅牢な検証とフォールバックを実装。
  - テストのために _call_openai_api をモンキーパッチで差し替え可能。
- .env パーサ:
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などをサポート。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョン対策（空チェックを実施）。
  - SQL の日付取得では型変換を安全に処理。

### 必要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- OPENAI_API_KEY（score_news / score_regime 実行時に必要）
- KABUSYS_ENV（defaults: development。許容値: development, paper_trading, live）
- LOG_LEVEL（defaults: INFO。許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
- DUCKDB_PATH / SQLITE_PATH（デフォルトは data/kabusys.duckdb / data/monitoring.db）

---

今後のリリース予定（例）
- strategy / execution / monitoring の具体的な戦略実装と注文実行ロジックの追加
- 単体テスト・統合テストの拡充、CI ワークフローの追加
- ドキュメント（API リファレンス、運用手順）の整備

（以上）