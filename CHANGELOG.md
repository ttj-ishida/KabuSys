# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記録します。  
このファイルはコードベース（バージョン __0.1.0__）の初期リリース相当の変更履歴を、ソースコードの内容から推測して作成したものです。

リリース日はソース解析時点（2026-03-28）を使用しています。実際のリリース日・バージョン運用はプロジェクトの方針に従ってください。

## [Unreleased]
（今後の変更をここに記載）

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装。

### 追加 (Added)
- 基本パッケージ定義
  - pakage メタ情報として `kabusys.__version__ = "0.1.0"` を追加。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を追加（プロジェクトルート検出：.git または pyproject.toml）。  
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - robust な .env パーサ実装:
    - コメント行・空行スキップ、export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理。
  - 上書きポリシーと protected キー（OS 環境変数保護）を実装。
  - 必須設定取得用の _require ヘルパ (例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD)。
  - DB パスやログレベル、環境フラグ（development / paper_trading / live）などのプロパティを提供。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (`score_news`) を実装（news_nlp）。
    - OpenAI（gpt-4o-mini）を用いた JSON Mode を使用。
    - タイムウィンドウ：前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB クエリ）。
    - 銘柄ごとに複数記事を集約し、1 銘柄 1 スコアで ai_scores テーブルへ書込。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数/文字数トリム実装。
    - レスポンス検証（JSON 抽出、results 配列、code/score の検証）・スコア±1.0 クリップ。
    - エラー耐性：429/接続断/タイムアウト/5xx に対する指数バックオフ・リトライ、最終的に失敗したチャンクはスキップ（例外を投げず継続）。
  - 市場レジーム判定 (`score_regime`) を実装（regime_detector）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成により日次レジーム判定（bull / neutral / bear）。
    - ma200 の計算は target_date 未満のデータのみ使用しルックアヘッドを防止。
    - マクロニュースフィルタリング（キーワードリスト） → OpenAI に送信 → JSON 解析で macro_sentiment を取得。
    - API エラー時は macro_sentiment=0.0 でフォールバック。
    - DuckDB の market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。

- データレイヤ (kabusys.data)
  - カレンダー管理（calendar_management）を実装。
    - JPX カレンダーを扱う market_calendar テーブル向けのユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーがない場合は曜日ベース（週末除外）でフォールバック。
    - 夜間バッチ job (calendar_update_job) を実装（J-Quants から差分取得 → 保存、バックフィル、健全性チェック）。
  - ETL パイプライン（pipeline）および ETLResult データクラスを実装。
    - 差分取得、idempotent な保存（jquants_client の save_* を想定）、品質チェック（quality モジュール）を想定した構成。
    - ETLResult により取得件数・保存件数・品質問題・エラーを集約可能。
  - etl の公開インターフェースを data.etl で再エクスポート（ETLResult）。

- リサーチモジュール (kabusys.research)
  - ファクター計算（factor_research）:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR, 相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を実装。
    - DuckDB の prices_daily / raw_financials を参照し、(date, code) ペアの辞書リストを返すインターフェース。
  - 特徴量探索（feature_exploration）:
    - 将来リターン算出（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換（rank）を実装。
    - pandas 等外部依存なしで標準ライブラリと DuckDB を利用する実装。
  - research パッケージで主要関数群を __all__ にて公開。

- 共通ユーティリティ
  - DuckDB を用いた SQL+Python ハイブリッド実装で大量データ処理に対応。
  - 各モジュールで「ルックアヘッドバイアス防止」の設計方針（datetime.today()/date.today() を直接参照しない）を採用。
  - 多くの DB 書込み処理で冪等性とトランザクション（BEGIN/COMMIT/ROLLBACK）を意識した実装。

### 変更 (Changed)
- （初回リリースにつき過去バージョンからの変更履歴はありませんが）設計方針や API の詳細をドキュメント文字列（docstring）でコード内に明記。

### 修正 (Fixed)
- （初回リリース）実行時に想定されるエラー耐性を多数組み込み:
  - OpenAI 呼び出しの一時エラーに対するリトライ/バックオフ。
  - レスポンスパース失敗や予期しない型に対するフォールバック（スコア 0.0、または該当銘柄スキップ）。
  - DuckDB の executemany の空リスト問題に対応したガード。

### セキュリティ (Security)
- API キー等の取り扱いに関して、環境変数による注入を前提としており、.env 自動ロードを必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 明示的に必須環境変数未設定時は ValueError を送出して早期検出する実装。

---

注記:
- 実際のリリースノート作成時はコミットログや PR の内容（実装者メッセージ）を参照して詳細を補完してください。本ファイルは提示されたソースコードと docstring から推測して作成した初期 CHANGELOG です。