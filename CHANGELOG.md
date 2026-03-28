# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣習に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システムのコアライブラリの基盤機能を実装しました。主な追加点と設計方針は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開。
  - __all__ に data / strategy / execution / monitoring をエクスポート（モジュール構成の入口を確立）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント取り扱いに対応）。
  - .env 読み込み時に OS 環境変数を保護する protected キーセットの概念を導入（.env.local は上書き可能だが OS 環境変数は保護）。
  - Settings クラスを追加し、環境変数から各種設定値を取得する API を提供（必要な環境変数は取得時に検証してエラーを投げる）。
    - 例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等
  - env / log_level 等の値検証（有効な値のみ許容）。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI (gpt-4o-mini) を用いて各銘柄のセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
    - JSON Mode を用いた厳密なレスポンス期待、レスポンスのバリデーションとクリッピング実装。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、1 銘柄あたりの記事数／文字数制限 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライロジック。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスパース失敗や未知コードは安全に無視し、部分成功時に既存スコアを保護するために対象コードのみ DELETE→INSERT で置換する冪等書き込みを行う。
    - 公開 API: score_news(conn, target_date, api_key=None)、calc_news_window(target_date) など。
    - テスト容易性: OpenAI 呼び出し部分は _call_openai_api を介しており patch による差し替えが可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成で日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp 側の窓関数 calc_news_window と連携して取得、OpenAI（gpt-4o-mini）で JSON レスポンスを期待してスコア化。
    - API 呼び出し失敗時は macro_sentiment を 0.0 とするフェイルセーフ、スコアリング後は market_regime テーブルへ冪等書き込み。
    - 公開 API: score_regime(conn, target_date, api_key=None)
    - テスト容易性のためこちらも _call_openai_api を明示的に差し替え可能に設計。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar 未取得時は曜日（土日）ベースのフォールバックを採用。
    - カレンダー夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル、健全性チェックを含む）。
  - ETL パイプライン基盤 (pipeline, etl)
    - ETLResult dataclass を公開（ETL 実行結果の構造化、品質チェック結果やエラー一覧を保持）。
    - 差分取得／保存／品質チェックを想定したユーティリティを実装（jquants_client, quality モジュールとの協調を前提）。
    - DuckDB を前提としたテーブル最大日付取得／存在チェック等のユーティリティを提供。
    - ETL の設計方針: idempotent な保存（ON CONFLICT 相当）、部分失敗時に他データを保護する実装、バックフィル対応。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (research.factor_research)
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、20 日 ATR（volatility）、流動性指標等を DuckDB（prices_daily, raw_financials）から計算する関数群を追加: calc_momentum, calc_volatility, calc_value。
    - 入出力は (date, code) キーの dict リストを返す設計（外部 API や取引 API にはアクセスしない）。
  - 特徴量探索・統計 (research.feature_exploration)
    - 将来リターン計算 calc_forward_returns（任意ホライズン）、IC（スピアマンのランク相関）計算 calc_ic、ランク変換 rank、統計サマリ factor_summary を実装。
    - pandas 等外部ライブラリに依存しない純 Python 実装を意図。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの取り扱いは引数注入または環境変数 OPENAI_API_KEY を利用する設計。キー未設定時は ValueError を発生させることで誤った実行を防止。

### 既知の設計上の注意点 / 方針
- ルックアヘッドバイアス防止: 主要な処理（score_news, score_regime, 各種計算）は date.today() や datetime.today() を参照せず、明示的な target_date を受け取る設計。
- DuckDB 互換性: executemany に空リストを渡せないバージョン等を考慮した実装パターンを採用。
- フェイルセーフ: AI API の一時的失敗やレスポンスパース失敗は致命的例外にせず、部分的に fallback して継続する方針。
- テスト容易性: OpenAI 呼び出し箇所は内部的に纏められており patch で差し替え可能。

---

今後の予定（例）
- strategy / execution / monitoring の実装・公開
- jquants_client や quality モジュールの具現化・連携テスト
- CI/CD / 型チェック / 単体テストの充実

（注）本 CHANGELOG は現行ソースコードから推測して作成しています。実際のリリースノート作成時は変更履歴やコミットログを基に調整してください。