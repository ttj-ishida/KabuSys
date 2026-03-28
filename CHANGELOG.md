# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを用います。

現在のバージョン: 0.1.0 (初期リリース)

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報管理を追加（kabusys.__init__、バージョン 0.1.0）。
  - モジュールエクスポート整理（data, strategy, execution, monitoring 等を __all__ に定義）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml）により、CWD に依存しない自動 .env ロードを実現。
  - .env/.env.local の優先順位処理（OS 環境変数 > .env.local（上書き） > .env（未設定時のみ））。
  - export KEY=val、引用符付き値、インラインコメント、バックスラッシュエスケープに対応した .env パーサ実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを公開。
  - 必須環境変数が未設定の場合は明示的なエラー（ValueError）を発生させるヘルパーを実装。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント: news_nlp モジュールを追加（score_news を公開）。
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウ集約処理（calc_news_window）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数/文字数トリム付き）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（1回最大20銘柄）と JSON モード利用。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）と指数バックオフ。
    - レスポンスの厳密なバリデーションとスコア ±1.0 クリップ。
    - ai_scores テーブルへの冪等的書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト用に _call_openai_api を patch 可能な設計。
  - 市場レジーム判定: regime_detector モジュールを追加（score_regime を公開）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次レジーム判定（bull/neutral/bear）。
    - prices_daily からの MA 計算、raw_news からマクロ関連タイトル抽出、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価。
    - API エラー時のフォールバック（macro_sentiment=0.0）とリトライ処理。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、ROLLBACK を含む安全処理）。
    - 未来参照（datetime.today()/date.today()）を参照しない設計でルックアヘッドバイアス回避。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（pipeline モジュール）
    - ETLResult データクラスを導入し、ETL 実行結果・品質問題・エラーを構造化して返却可能に。
    - 差分更新・バックフィル・品質チェック・DuckDB 使用を前提とした設計方針を実装。
  - Calendar 管理（calendar_management）
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - JPX カレンダーを J-Quants から差分取得する夜間ジョブ（calendar_update_job）を実装（バックスフィル、健全性チェック、保存処理）。
    - 最大探索日数・バックフィル日数等の安全パラメータを導入。
  - jquants_client を利用したデータ取得/保存のインターフェース設計（fetch/save の想定）。

- 研究（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金等）、バリュー（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB クエリ中心で外部 API に依存しない設計。
    - データ不足時は None を返す安全な挙動。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランキング（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で完結する実装。
  - 研究用ユーティリティ（zscore_normalize の再エクスポート等）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- OpenAI / API 呼び出しに関する堅牢性の強化
  - JSON パース失敗や API の 5xx、タイムアウト、レート制限に対するリトライ/フォールバック処理を追加。
  - API レスポンスの不正（JSON 以外の余分な前後テキスト等）に対しても可能な限り復元・検証する処理を実装。

- DuckDB 書き込み時の冪等性とエラー回復
  - BEGIN/COMMIT/ROLLBACK の扱い、ROLLBACK が失敗した場合の警告ログ出力など DB エラー耐性を向上。

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）を利用するため、実行環境での適切な秘匿管理が必要。
- OpenAI API キー未設定時には AI 関連関数が ValueError を投げ、明示的に扱うように設計。

---

注記:
- 多くのモジュールは DuckDB を前提とした SQL クエリを使用しています。運用時は DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が正しく準備されていることを確認してください。
- AI 系機能は外部 API（OpenAI）に依存しており、レスポンス形式や API クォータによって挙動が変わる可能性があります。テスト時には _call_openai_api の差し替え（mock）を利用してください。