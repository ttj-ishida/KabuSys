# Changelog

すべての注記は Keep a Changelog 準拠です。  
このファイルはコードベース（kabusys パッケージ）のソースから推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 初回リリース
初期実装。日本株自動売買システムの基盤的なモジュール群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージメタ情報
  - kabusys パッケージのバージョンを 0.1.0 に設定。
  - パッケージトップで外部 API の利用やサブパッケージ参照のための公開インターフェースを定義（data, strategy, execution, monitoring を __all__ で公開）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート自動検出ロジック: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを決定（配布後も動作）。
  - .env パーサ実装:
    - コメント行・空行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートを考慮し、バックスラッシュエスケープを処理してクォート閉じを正しく扱う。
    - クォートなしの場合は '#' の前がスペース/タブの場合に限りインラインコメントを除去。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。`.env.local` は既存環境変数を上書き可能（ただし OS 環境変数は保護）。
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用可能）。
  - Settings クラスに環境変数アクセス用プロパティを提供（必須項目は未設定時に ValueError を送出）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値設定
    - KABUSYS_ENV 値検証（development / paper_trading / live のみ許容）
    - LOG_LEVEL 値検証（DEBUG/INFO/...）

- データ関連ユーティリティ (src/kabusys/data/*)
  - calendar_management.py:
    - JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未登録の場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API（jquants_client を仮定）から差分取得し market_calendar を冪等的に保存。バックフィル日数や健全性チェックを実装。
  - etl.py:
    - ETLResult の公開（pipeline.ETLResult を再エクスポート）。
  - pipeline.py:
    - ETL 実行フローの基礎（差分取得、保存、品質チェックを想定）に対応するユーティリティと ETLResult データクラスを実装。
    - ETLResult は取得数・保存数・品質問題・エラー一覧を保持。has_errors / has_quality_errors プロパティ、辞書化メソッド to_dict を提供。
    - テーブル存在チェックやテーブル内最大日付取得のヘルパ実装。

- AI（ニュース NLP / レジーム判定） (src/kabusys/ai/*)
  - news_nlp.py:
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメントを算出して ai_scores テーブルへ書き込む処理を実装。
    - ニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供する calc_news_window。
    - バッチ処理: 1 API 呼び出しで最大 20 銘柄を処理（_BATCH_SIZE=20）。
    - 1銘柄あたり最大記事数と文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でプロンプト肥大化に対処。
    - JSON Mode を利用し、レスポンスをバリデーションしてスコアを ±1.0 にクリップ。
    - エラーハンドリング: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。失敗時は当該チャンクをスキップし他銘柄への影響を抑制。
    - DB 書き込みはトランザクションで実行（DELETE → INSERT）し、部分失敗時に既存データを保護。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api で抽象化して unittest.mock で差し替え可能。
  - regime_detector.py:
    - 日々の市場レジーム判定ロジックを実装（'bull' / 'neutral' / 'bear'）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成してレジームスコアを算出。
    - マクロニュースは news_nlp.calc_news_window により期間を決定し、raw_news からマクロキーワードでフィルタ。
    - OpenAI (gpt-4o-mini) を用いてマクロセンチメントを JSON 出力で取得。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - レジームスコアのクリップ・閾値判定（bull / bear の閾値）を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
    - テスト容易性: _call_openai_api を差し替え可能。

- Research / ファクター計算 (src/kabusys/research/*)
  - factor_research.py:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均出来高・売買代金）およびバリュー（PER, ROE）等を DuckDB の prices_daily / raw_financials データを使って計算する関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - データ不足や条件未達時は None を返す等の堅牢性を実装。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - calc_forward_returns は任意ホライズン（デフォルト [1,5,21]）に対応し、SQL で一括取得する設計。
    - calc_ic はスピアマンランク相関を実装し、データ不足時は None を返す。
  - research パッケージ __init__ で主要関数を再公開。data.stats.zscore_normalize を再エクスポート。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 削除 (Removed)
- なし（初回リリース）

### 非推奨 (Deprecated)
- なし（初回リリース）

### セキュリティ (Security)
- OpenAI API キーは明示的に引数で渡すことが可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定の場合は ValueError を送出して安全に失敗します。

## 注意事項（設計方針・運用上のポイント）
- ルックアヘッドバイアス防止:
  - news_nlp / regime_detector 等では datetime.today() / date.today() を直接参照せず、関数呼び出し側で target_date を与える設計を採用。
  - DB クエリでは date < target_date 等の排他条件を利用してルックアヘッドを防止。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）呼び出しの失敗は個別にフォールバック（例: macro_sentiment=0.0）またはチャンクスキップで処理。致命的エラーを投げるのではなく処理継続を優先する設計。
- テスト容易性:
  - OpenAI 呼び出しをラップする関数（_call_openai_api）を各モジュールで提供し、ユニットテストでモック差替えが可能。
- DuckDB 互換性考慮:
  - executemany に空配列を渡さない等、DuckDB のバージョン差異に配慮した実装を行っている箇所あり。

---

（この CHANGELOG はソースコードの実装内容を元に推測して作成しています。実際のリリースノートには追加の運用情報や既知の問題、マイグレーション手順等を追記してください。）