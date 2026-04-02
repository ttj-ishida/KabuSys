# Changelog

全ての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-02
初回リリース。日本株自動売買プラットフォームのコアモジュール群を実装しました。
主な追加点および設計方針は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（バージョン: 0.1.0）。
  - パッケージ公開モジュール一覧に data / strategy / execution / monitoring を想定。

- 設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定を自動読込する仕組みを実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD 非依存で読み込み。
    - 読み込み優先順位：OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーの実装（コメント、export プレフィックス、クォートとバックスラッシュエスケープに対応）。
  - Settings クラスを追加し、以下の設定プロパティを提供（環境変数名を内部で参照）：
    - J-Quants / kabu API / Slack / データベースパス（DuckDB/SQLite）/監視設定（PID ファイル・閾値）/システム設定（環境、ログレベル, is_live 等）
  - 必須環境変数が未設定の場合は明示的な ValueError を発生させる `_require` を実装。

- AI（自然言語処理）機能 (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数/文字数制限、JSON Mode レスポンス検証、スコアの ±1 クリップ、DuckDB への冪等書き込み（DELETE → INSERT）を実装。
    - エラー耐性：429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスパース失敗や API エラー時はフェイルセーフでスキップ（例外を全体に伝播させない）。
    - テスト容易性のため、OpenAI 呼び出し点に差し替え可能なプライベート関数（_call_openai_api）を用意。

  - regime_detector.score_regime
    - ETF 1321（Nikkei225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - ma200 比率計算、マクロニュース取得（キーワードフィルタ）、OpenAI 呼び出し（gpt-4o-mini）、レジームスコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
    - OpenAI 呼び出しは別実装にしてモジュール結合を避ける設計。

- データ基盤 (kabusys.data)
  - calendar_management
    - JPX カレンダー管理（market_calendar）を扱うユーティリティ群を実装。
    - 営業日判定・前後営業日取得・期間内営業日取得・SQ 日判定機能（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - カレンダーが未導入の場合は曜日ベース（平日）でフォールバックする一貫した設計。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル機能・健全性チェックを含む）。
  - pipeline / ETL
    - ETLResult データクラスを公開（kabusys.data.etl は pipeline.ETLResult を再エクスポート）。
    - 差分更新、保存（jquants_client の save_* を利用して冪等保存）、品質チェック（quality モジュール連携）を想定したパイプライン土台を実装。
    - DuckDB に対するテーブル存在チェックや最大日付取得などのユーティリティ実装。
    - ETLResult は品質問題を辞書化してログ等に出力可能。

- 研究/因子分析 (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン・200 日 MA 乖離）、ボラティリティ（20 日 ATR、ATR 比率）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER・ROE）等の因子計算関数（calc_momentum, calc_volatility, calc_value）を実装。
    - DuckDB を用いた SQL ベースの計算（過去スキャン範囲のバッファ等を考慮）。
    - データ不足時の None 処理など堅牢な動作。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず、純粋 Python + DuckDB で動作することを想定。
  - 研究用ユーティリティをまとめて再エクスポートする __init__ を提供。

### 変更 (Changed)
- （初回リリースのため変更はなし）

### 修正 (Fixed)
- （初回リリースのため修正はなし）

### セキュリティ (Security)
- 環境設定読み込みで OS 環境変数を保護する仕組み（protected set）を備え、.env からの上書きを制御可能。
- OpenAI API キーは明示的に引数で注入可能。未設定時は ValueError を発生させて誤動作を防止。

### 設計上の注意 / 既知の動作
- ルックアヘッドバイアス回避のため、各処理は datetime.today()/date.today() を安易に参照せず、呼び出し側から target_date を受け取る設計。
- OpenAI 呼び出し箇所にはリトライ処理とフェイルセーフ（失敗時にスコア 0 またはスキップ）を入れているため、API の不安定さに耐性がある。
- DuckDB に関する互換性（executemany の空リスト制約等）を考慮した実装が行われている。
- テスト容易性を考え、OpenAI 呼び出しの差し替えポイントや api_key の注入箇所を意図的に提供。

---

注: この CHANGELOG は与えられたソースコードの内容から推測して作成したものであり、実際のリリース履歴や運用上の注記とは異なる場合があります。必要に応じて項目の追加・修正を行ってください。