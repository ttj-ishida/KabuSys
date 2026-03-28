# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、本リポジトリに含まれるコードから推測できる初期リリース情報を日本語でまとめたものです。

なお、バージョン番号はパッケージ定義（src/kabusys/__init__.py の __version__）に合わせています。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買およびリサーチ基盤のコア機能群を追加。
  - パッケージ公開情報:
    - バージョン: 0.1.0
    - エクスポートモジュール: data, strategy, execution, monitoring（__all__）

- 環境変数・設定管理 (kabusys.config)
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env / .env.local の読み込み順: OS 環境変数 > .env.local > .env。  
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - .env パース機能を強化:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱いに対応。
  - Settings クラスを導入し、環境変数からアプリ設定を安全に取得:
    - 必須キー取得用の _require（未設定時は ValueError を送出）。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション。
    - デフォルト DuckDB/SQLite パス（data/kabusys.duckdb, data/monitoring.db）

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp)
    - raw_news, news_symbols を元に銘柄ごとのニュースを集約し、OpenAI Chat API (gpt-4o-mini) を用いてセンチメントを算出し ai_scores テーブルへ書き込み。
    - 処理の特徴:
      - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で算出（UTC naive datetime を返す）。
      - 銘柄ごとに記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトリム。
      - バッチ処理（最大 _BATCH_SIZE=20 銘柄／回）と JSON mode を利用した堅牢な API 呼び出し。
      - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライの実装。
      - レスポンスの厳密なバリデーション（JSON 抽出、results 配列チェック、スコア数値化、±1.0 のクリップ）。
      - DuckDB への書き込みは冪等性を担保（対象コードのみ DELETE → INSERT）。部分失敗時に既存データを保護。
      - テスト容易性のため _call_openai_api 関数は差し替え可能（unittest.mock.patch を想定）。

  - 市場レジーム判定 (regime_detector)
    - 日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ書き込む。
    - 判定ロジック:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成。
      - ma200_ratio の計算（target_date 未満のデータのみ使用：ルックアヘッド防止）。
      - raw_news からマクロキーワードでフィルタしたタイトルを取得。
      - OpenAI（gpt-4o-mini）でマクロセンチメント評価（記事なしは LLM 呼び出しを省略、失敗時は macro_sentiment = 0.0 としフェイルセーフ）。
      - スコア合成と閾値判定（_BULL_THRESHOLD / _BEAR_THRESHOLD）。
      - 結果の冪等的 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - API 呼び出し部分は news_nlp とは別実装とし、モジュール間結合を低減。

- データ基盤 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。
    - market_calendar を用いた営業日判定ユーティリティを提供:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB にデータがない場合は曜日ベース（土日非営業日）でフォールバックする堅牢な設計。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル、健全性チェックを実装。
    - J-Quants クライアント（jquants_client.fetch_market_calendar / save_market_calendar）との連携を想定。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（pipeline.ETLResult を re-export）。
    - ETLResult は取得件数・保存件数・品質問題リスト・エラーリスト等を保持し、辞書化サポート（品質問題は (check_name,severity,message) 化）。
    - pipeline モジュールに含まれるユーティリティ:
      - 差分更新（最終取得日ベース）・バックフィルの扱い・品質チェックの収集方針を実装方針として明記。
      - DuckDB テーブル存在確認や最大日付取得などの内部ユーティリティを実装。

- リサーチ（研究）モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム: calc_momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ/流動性: calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比）
    - バリュー: calc_value（PER、ROE、raw_financials の最新値を使って計算）
    - 設計: DuckDB の prices_daily/raw_financials のみ参照、結果は (date, code) キーの dict リストで返却
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算: calc_forward_returns（horizons の検証、1 クエリで複数ホライズン取得）
    - IC 計算: calc_ic（Spearman のランク相関）
    - ランク変換: rank（同順位は平均ランク処理、丸めて ties を安定化）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
  - 研究ユーティリティの再公開: zscore_normalize を data.stats からインポートして公開

### Changed
- （初回リリースのため特になし）

### Fixed
- （初回リリースのため特になし）

### Security
- OpenAI API キーや外部サービスのトークン類は環境変数経由で取得。Settings で必須チェックを行い、未設定時は ValueError を送出して明示的に失敗する設計。

### Notes / 実装上の重要ポイント（アップグレード／導入時の注意）
- 必要な環境変数:
  - OPENAI_API_KEY（news_nlp / regime_detector の API 呼び出し。api_key を明示的に渡すことも可能）
  - JQUANTS_REFRESH_TOKEN（Settings.jquants_refresh_token が必須）
  - KABU_API_PASSWORD（kabu API）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知）
  - KABUSYS_ENV（development / paper_trading / live のいずれか）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- .env 自動ロードはプロジェクトルート検出に依存。配布後やインストール環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して挙動を制御することを推奨。
- DuckDB の対象テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）はスキーマ整備が必要。ETL／保存関数（jquants_client 側）との連携が前提。
- OpenAI 呼び出し部分は内部で差し替え（モック化）できるように設計しているため、テスト時は _call_openai_api をモックする等して外部 API を回避可能。
- AI レスポンスのパースは堅牢化しているが、LLM の応答仕様変更により挙動が変わる可能性あり。ログとフェイルセーフ（0.0 やスキップ）により運用継続を優先する設計。

---

今後のリリースでは以下が想定されます（推測）:
- strategy / execution / monitoring の具体実装追加（注文ロジック・実行エンジン・監視アラート）
- jquants_client 実装の詳細公開と ETL の運用改善
- 単体テスト・統合テスト、CI/CD ワークフローの整備
- ドキュメント（API 仕様、DB スキーマ、運用手順）の拡充

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。）