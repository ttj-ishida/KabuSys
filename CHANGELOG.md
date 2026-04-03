# CHANGELOG

すべての主要な変更は Keep a Changelog の方針に従って記載しています。  
リリースはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」の基本機能群を実装しました。以下はコードベースから推測できる主な追加点・設計方針です。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化。__version__ = "0.1.0" を設定し、主要サブパッケージ（data, research, ai, ...）をエクスポート。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込み機能を実装。
  - 自動読み込み機構:
    - プロジェクトルートを .git または pyproject.toml から探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト向け）。
  - .env パーサーは以下をサポート／考慮:
    - 空行・コメント行（#）の扱い、`export KEY=val` 形式、
    - シングル／ダブルクォート内でのバックスラッシュエスケープ対応、
    - クォートなし時のインラインコメント扱い（直前がスペース or タブの場合のみ）。
  - 環境値取得用 Settings クラスを実装（jquants refresh token、kabu API の設定、LINE トークン、DB パス、監視フラグ、閾値など）。
  - 値のバリデーション（KABUSYS_ENV の限定値、LOG_LEVEL の限定値）・ユーティリティプロパティ（is_live / is_paper / is_dev）を提供。
  - 必須値未設定時は明示的に ValueError を送出する _require() を実装。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）:
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST の記事）を厳密に計算（UTC naive datetime を DB 比較に使用）。
    - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事／3000 文字にトリムしてプロンプトに含めるトークン肥大化対策。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、各要素の code/score の型チェック、未知コード無視、数値かつ有限値の検査）。
    - スコアは ±1.0 にクリップ。ai_scores テーブルへは取得に成功した銘柄のみ置換（DELETE → INSERT）して部分失敗時に既存データを保護。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）、未指定時は ValueError。
    - テスト容易性のため OpenAI 呼び出しを _call_openai_api 関数に抽象化（パッチ差し替え可）。
  - 市場レジーム判定（ai.regime_detector.score_regime）:
    - ETF 1321（日経225 連動）を用いた 200 日移動平均乖離（重み 70%）と、マクロ記事の LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を決定。
    - マクロ記事はマクロ関連キーワードでフィルタ（キーワードの一覧を定義）。
    - LLM 呼び出しは gpt-4o-mini の JSON 出力を想定。API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - スコアのクリップ、閾値に基づくラベル付け、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）、未指定時は ValueError。
    - OpenAI 呼び出しの再試行や 5xx の扱いなど堅牢なエラーハンドリングを実装。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（data.calendar_management）:
    - market_calendar テーブルを利用した営業日判定 API: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB にデータがない場合は曜日ベース（週末を非営業日）でフォールバックする一貫したロジック。
    - 夜間バッチ（calendar_update_job）: J-Quants API から差分取得し market_calendar を冪等保存。バックフィルや健全性チェック（過剰に未来日がある場合はスキップ）を実装。
    - 最大探索範囲により無限ループ回避。
  - ETL パイプライン（data.pipeline / data.etl）:
    - ETLResult データクラスを公開（target_date、取得/保存件数、品質問題リスト、エラーリスト等）。
    - 差分取得・保存・品質チェックを想定した設計（J-Quants クライアント経由の差分フェッチ、idempotent な保存、品質チェックの収集と報告）。
    - バックフィル日数設定や calendar lookahead などの運用パラメータを定義。
    - エラーと品質問題の区別（品質問題は収集して ETLResult に含め、致命的であれば呼び出し元で対処可能にする設計）。

- リサーチ機能（kabusys.research）
  - ファクター計算（research.factor_research）:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）等を DuckDB と SQL で計算。
    - データ不足時は None を返す等、安全な扱い。
    - 全関数は prices_daily / raw_financials のみ参照する（外部発注等にはアクセスしない）。
  - 特徴量探索（research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリと SQL で完結する設計。
    - calc_forward_returns は horizons の柔軟化と入力検証（正の整数かつ 252 以下）を行う。

- テスト・運用に配慮した実装
  - DuckDB を主要なローカル DB として使う設計（Path を返す設定、DUCKDB_PATH 等）。
  - OpenAI 呼び出しや .env 読み込みなどを差し替え可能にしてユニットテストがしやすい構造。
  - ルックアヘッドバイアスを防ぐため、内部で datetime.today() / date.today() を直接参照しない設計原則を各モジュールで踏襲。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの取り扱いは環境変数または引数注入を想定。機密情報の自動ログ出力を行わない設計が示唆される（ただし運用での注意は必要）。

---

注記:
- 上記はソースコードの内容から推測した CHANGELOG です。実際のリリースノートとして公開する際は、コミット履歴や ISSUE/PR 情報、テスト結果、既知の制約・回避策などを補足することを推奨します。