# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョンは __version__ = 0.1.0 です。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース

### 追加 (Added)
- パッケージの公開エントリポイントを追加
  - パッケージ名: kabusys
  - __all__ に data, strategy, execution, monitoring を定義。

- 設定/環境変数管理モジュールを追加 (kabusys.config)
  - .env/.env.local ファイルの自動読み込み機能（プロジェクトルートの検出は .git または pyproject.toml を使用）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - export KEY=val、クォート、インラインコメント等への柔軟なパース実装。
  - 環境変数取得ユーティリティ Settings を追加。主要プロパティ：
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path (デフォルト data/kabusys.duckdb), sqlite_path (デフォルト data/monitoring.db)
    - env（development / paper_trading / live の検証）、log_level の検証
    - is_live / is_paper / is_dev のブールプロパティ
  - 必須環境変数未設定時は ValueError を送出する _require 関数を提供。

- ニュースNLP（AI）モジュールを追加 (kabusys.ai.news_nlp)
  - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）の JSON mode でセンチメントを取得。
  - タイムウィンドウ計算（前日15:00 JST 〜 当日08:30 JST）を calc_news_window にて提供。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、トリム（記事数・文字数制限）によりトークン肥大を抑制。
  - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
  - レスポンス検証ロジック（_validate_and_extract）を実装し、不正なレスポンスはスキップ。
  - ai_scores テーブルへの冪等的な書き込み（対象コードのみ DELETE→INSERT）により部分失敗時の既存データ保護。

- 市場レジーム判定モジュールを追加 (kabusys.ai.regime_detector)
  - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
  - OpenAI を用いたマクロセンチメント評価を実装。空記事時は LLM 呼び出しを行わない。
  - API 呼び出しは再試行ロジックとフェイルセーフ（失敗時 macro_sentiment = 0.0）を組み込み。
  - DuckDB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
  - ルックアヘッドバイアスを避ける設計（datetime.today() を直接参照しない、データクエリに date < target_date を利用）。

- リサーチ（研究）モジュールを追加 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率の算出（データ不足時の None 処理）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率の算出。
    - calc_value: raw_financials から取得した EPS/ROE と当日株価を用いて PER/ROE を算出。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで計算（horizons の入力検証あり）。
    - calc_ic: スピアマンランク相関による IC 計算（必要レコード数未満 → None）。
    - rank: 平均ランク（同順位は平均ランク）実装。浮動小数の丸めによる ties 対応。
    - factor_summary: count/mean/std/min/max/median 等の統計要約を計算。
  - zscore_normalize を data.stats から再エクスポート。

- データプラットフォーム関連モジュールを追加 (kabusys.data)
  - calendar_management:
    - market_calendar ベースの営業日判定・次/前営業日の取得・期間内営業日列挙・SQ 判定等の API を提供。
    - market_calendar 未取得時は曜日ベース（土日非営業）でフォールバック。DB 登録値優先の一貫した挙動を実装。
    - calendar_update_job: J-Quants から差分取得し保存。バックフィル、健全性チェック（極端な未来の日付はスキップ）を実装。
  - pipeline / etl:
    - ETLResult データクラスを追加（取得数、保存数、品質問題、エラー概要等を格納、to_dict() を提供）。
    - _get_max_date 等の ETL ヘルパーを実装。
    - 差分取得・バックフィルポリシー・品質チェック設計に対応する基盤を実装。
  - jquants_client（参照のみ）との連携を前提に実装（fetch/save 呼び出しを使用）。

- テスト容易性向上
  - OpenAI 呼び出し箇所（news_nlp と regime_detector）の _call_openai_api を patch/差し替え可能に実装。

### 変更 (Changed)
- （初回リリースのため過去の変更はなし）

### 修正 (Fixed)
- （初回リリースのため既知のバグ修正はなし）

### 削除 (Removed)
- （初回リリースのためなし）

### セキュリティ (Security)
- OpenAI API キーおよび各種シークレットは環境変数で管理する設計:
  - OPENAI_API_KEY（news_nlp, regime_detector）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後の環境では明示的に環境を設定することを推奨。
- 設定値の検証（env, log_level）により不正な設定値による誤動作を早期に検出。

### 注意事項 / 既知の設計方針
- ルックアヘッドバイアス防止のため、日付計算はすべて呼び出し側から与えられる target_date を基準に行い、datetime.today() / date.today() を直接参照しない実装が多く採用されています（ただし calendar_update_job は実行日の today を参照）。
- DuckDB を前提とした SQL 実装が中心であり、executemany に空リストを与えない等の互換性に配慮した実装が行われています（DuckDB 0.10 の制約を考慮）。
- AI 呼び出しはフェイルセーフ設計（API 失敗時はスコア 0.0 にフォールバック、例外を上位に伝播しない）により、外部 API 障害時にもパイプライン全体が停止しにくい設計です。
- news_nlp / regime_detector の両モジュールは gpt-4o-mini かつ JSON mode を期待するプロンプト定義を利用しています。返却形式の厳密な遵守を前提としていますが、パースに失敗した場合はログを残してスキップします。

---

今後のリリースでは、以下を想定しています（例）:
- strategy / execution / monitoring モジュールの実装と統合テスト
- エンドツーエンド ETL とバックテストの CI パイプライン整備
- ドキュメント (README, Usage examples, API リファレンス) の充実

もし特定の機能のリリース履歴（より詳細な変更履歴）を望まれる場合は、どのモジュール／機能に注目したいか教えてください。