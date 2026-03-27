# Changelog

すべての重要な変更をここに記載します。本プロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣習に従います。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-27

初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。公開サブパッケージ: data, strategy, execution, monitoring。

- 環境設定 / .env ローダー
  - src/kabusys/config.py
    - .env および .env.local のプロジェクトルート自動読み込み機能（プロジェクトルートは .git または pyproject.toml で検出）。
    - export KEY=val 形式やクォート/エスケープ、インラインコメント処理に対応するパーサ実装。
    - 自動ロード無効化オプション: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス等のプロパティ）。
    - 必須環境変数未設定時は ValueError を発生。
    - 環境変数検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- データ（Data Platform）ユーティリティ
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar）用ロジック。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定関数。
    - カレンダーデータがない場合の曜日ベースフォールバック実装。
    - calendar_update_job による J-Quants からの差分取得と保存処理（バックフィルや健全性チェックを含む）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの基礎（ETLResult データクラスを再エクスポート）。
    - 差分取得・保存・品質チェックのためのユーティリティ。DuckDB を前提に実装。
    - テーブル存在チェック、最大日付取得などの内部ユーティリティを提供。
  - src/kabusys/data/__init__.py（プレースホルダ）

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum ファクター（1M/3M/6M リターン、200日 MA 乖離）。
    - Volatility / Liquidity ファクター（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）。
    - Value ファクター（PER、ROE：raw_financials からの取得）。
    - DuckDB を用いた SQL + Python 実装、データ不足時の None ハンドリング。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns：任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（スピアマンランク相関）。
    - rank, factor_summary 等の統計/ユーティリティ関数。
  - src/kabusys/research/__init__.py にて主要関数を再エクスポート。

- AI（LLM）関連
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとのニュースを LLM（gpt-4o-mini）でセンチメント評価。
    - タイムウィンドウ定義（前日15:00 JST ～ 当日08:30 JST）、バッチサイズ、文字数/記事数トリム設定。
    - OpenAI API 呼び出しの再試行（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）。
    - レスポンスのバリデーション（JSON 抽出、results リスト、code と score の検証）、スコア ±1.0 クリップ。
    - 成功した銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT、部分失敗で既存データを保護）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（Nikkei 225 連動型）の 200 日 MA 乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - _calc_ma200_ratio、_fetch_macro_news、_score_macro（OpenAI 呼び出しと再試行）の実装。
    - レジーム合成ロジック、閾値（BULL/Bear）および market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 失敗時は macro_sentiment=0.0 としてフェイルセーフ。
  - 両モジュールとも OpenAI クライアント（OpenAI(api_key=...)）を使用。デフォルトモデルは gpt-4o-mini。
  - テスト用に内部 _call_openai_api をモック可能な設計。

### 変更 (Changed)
- N/A（初回リリース）

### 修正 (Fixed)
- N/A（初回リリース）

### セキュリティ (Security)
- N/A（初回リリース）

### ドキュメント / 注意事項 (Notes)
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY などの設定が必要な機能があります。Settings クラス経由で取得するため、環境変数または .env を適切に設定してください。
- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml をベース）を探索して .env / .env.local を自動読み込みします。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ
  - 多くの処理は DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を前提とします。ETL 実行前にスキーマと該当テーブルを準備してください。
- LLM 呼び出しの挙動
  - OpenAI API 呼び出しは JSON mode を想定しており、API レスポンスのパース失敗や API エラーはログ出力のうえフェイルセーフ（0 やスキップ）で続行する設計です。
  - レート制限・ネットワーク障害・5xx サーバーエラーに対して指数バックオフでリトライします（デフォルト retry 回数等は各モジュールの定数で調整可能）。
- ルックアヘッドバイアス対策
  - 各関数は内部で datetime.today()/date.today() を参照しないよう設計されており、target_date 引数ベースで動作します。バックテストや研究用途での使用時にルックアヘッドバイアスを軽減しています。

### 既知の制約 / TODO（将来的な改善候補）
- raw_financials からの PBR / 配当利回りは未実装（calc_value の拡張余地）。
- 一部の DuckDB バインド挙動（list 型パラメータの互換性）を避けるため executemany を用いた実装となっており、DuckDB バージョン依存の注意が必要。
- news_nlp と regime_detector は内部で別実装の _call_openai_api を持つ（モジュール結合を避ける設計）。テスト用にモックしやすいが、共通化の検討余地あり。

---

今後のリリースでは、ETL の具体的な実装（jquants_client のインタフェース）、strategy / execution / monitoring サブパッケージの実装拡張、テストカバレッジと CI ワークフローの追加を予定しています。

Contributors: 初期実装チーム（実装者情報はリポジトリのコミット履歴を参照してください）。