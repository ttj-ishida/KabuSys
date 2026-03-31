# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/）に準拠しています。  

なお、本CHANGELOGは与えられたコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」の基礎機能群を提供します。以下の機能・モジュールを追加しました。

### 追加 (Added)
- パッケージ初期化
  - `kabusys` パッケージの基本情報を追加（__version__ = "0.1.0"）。
  - パッケージの公開モジュールを `__all__ = ["data", "strategy", "execution", "monitoring"]` として定義。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード:
    - プロジェクトルート（.git または pyproject.toml を探索）を検出して `.env` → `.env.local` の順で読み込み。
    - OS 環境変数を保護するための protected キーセットを考慮（`.env.local` は上書き可能だが OS の既存キーは保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト等で利用）。
  - .env パーサーは以下に対応:
    - 空行・コメント行（#）の無視、`export KEY=val` 形式の対応。
    - シングル/ダブルクォートされた値のバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント扱いの判定（直前が空白/タブの場合に '#' をコメントとみなす）。
  - Settings で主要設定項目をプロパティとして提供（J-Quants, kabuステーション, Slack, DB パス, 監視閾値, 環境種別/ログレベルのバリデーション等）。
  - 環境変数未設定の必須値は _require() で ValueError を投げる設計。

- AI（自然言語処理）モジュール (`kabusys.ai`)
  - `news_nlp.score_news`:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントを評価し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）に対応する変換ロジック。
    - 1銘柄あたり最大記事数／文字数でトリム、最大バッチサイズで分割して API 呼び出しを実行。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code と score の検証、数値の有限性チェック）、スコアを ±1.0 にクリップ。
    - 429/接続断/タイムアウト/5xx に対して指数バックオフでリトライ。失敗はログに残し該当チャンクをスキップするフェイルセーフ設計。
    - テスト用に _call_openai_api をモック差し替え可能。
  - `regime_detector.score_regime`:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - prices_daily および raw_news からデータ取得。MA 計算は target_date 未満のデータのみ利用してルックアヘッドを防止。
    - マクロキーワードでニュースをフィルタ、OpenAI 呼び出しは最大リトライを持ち失敗時は macro_sentiment=0.0 にフォールバック。
    - OpenAI 呼び出し関数は news_nlp と意図的に別実装（モジュール結合軽減）。

- データプラットフォーム関連 (`kabusys.data`)
  - ETL インターフェースの公開 (`kabusys.data.etl` が pipeline.ETLResult を再エクスポート)。
  - `pipeline.ETLResult` データクラス:
    - ETL 実行結果（取得件数・保存件数・品質チェック結果・エラー）を表現、辞書化ユーティリティを提供。
  - `pipeline`（ETL パイプライン）設計方針とユーティリティ関数（テーブル存在検査、最終日取得ロジック等）を実装（差分取得、バックフィル、品質チェック対応を想定）。
  - `calendar_management`:
    - JPX カレンダー管理（market_calendar）と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - カレンダーが無い場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新。直近のバックフィルと健全性チェックを実装。
    - 最大探索日数などの安全機構（_MAX_SEARCH_DAYS 等）を導入。

- リサーチ / ファクター計算 (`kabusys.research`)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB 上の SQL と Python の組合せで計算する関数を提供。
    - データ不足時の扱い（None を返す）やログ出力の実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
    - calc_ic は Spearman（ランクの Pearson）を実装、十分な有効レコードがない場合は None を返す。

### 変更 (Changed)
- 初回リリースのため過去変更なし（コード構成上の設計方針・制約を CHANGELOG に明記）。

### 修正 (Fixed)
- 初回リリースのため過去修正なし。

### 削除 (Removed)
- 初回リリースのためなし。

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を使用する設計。API 呼び出し失敗時は機能を安全にデグレード（スコア → 0.0 やスキップ）するフェイルセーフを導入。

---

メモ（実装上の注目ポイント・設計方針）
- ルックアヘッドバイアス防止: 主要な解析/スコアリング関数は内部で datetime.today()/date.today() を直接参照せず、必ず caller が target_date を指定する設計。
- DuckDB を主要なローカル分析用データベースとして利用。
- DB 書き込みは冪等性を意識（DELETE → INSERT / ON CONFLICT 相当の扱い）し、部分失敗時に既存データを不要に消さない配慮あり。
- OpenAI 呼び出しは JSON mode を利用し、レスポンスの堅牢なパースと検証を行う。テスト容易性のため内部 API 呼び出し関数をモック可能にしている。
- 外部依存を最小化（pandas 等を使わずに標準ライブラリ＋duckdb）しており、研究・検証環境でも軽量に動作する想定。

もしより詳細なリリースノート（関数ごとの使用例、入出力フォーマットの具体例、既知の制限など）を希望される場合は、どのモジュール／関数について詳述するかを教えてください。