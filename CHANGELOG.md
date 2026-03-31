# CHANGELOG

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に基づきます。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回公開リリース。

### 追加 (Added)
- パッケージ基本
  - kabusys パッケージ初期実装を追加。公開モジュール群: data, research, ai, execution, strategy, monitoring（__all__ にて公開）。
  - バージョン情報を `src/kabusys/__init__.py` にて `0.1.0` として定義。

- 設定 / 環境変数管理 (`src/kabusys/config.py`)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートの自動探索（.git または pyproject.toml を基準）によりカレントディレクトリに依存しない読み込みを実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS 側の環境変数を保護するための protected キーセットを導入し、override 挙動を制御。
    - 自動読み込みの無効化オプション `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - .env のパース機能強化:
    - export 形式のサポート、クォート内のエスケープ処理、インラインコメント判定の厳密化。
  - `Settings` クラスを実装して設定値をプロパティ経由で取得（必須項目は _require 関数で検証）。
    - J-Quants / kabuステーション / Slack / DB パス / 監視設定（PID ファイル、閾値）/ 環境種別・ログレベル等をプロパティで提供。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI モジュール（OpenAI を用いた NLP）
  - ニュースNLP (`src/kabusys/ai/news_nlp.py`)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄毎のセンチメント（ai_score）を算出。
    - バッチ処理（最大 20 銘柄/チャンク）、記事数/文字数制限、レスポンスバリデーション、スコア ±1 にクリップ。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフ）とフェイルセーフ（失敗時はスキップして継続）。
    - DuckDB への冪等書き込み（DELETE → INSERT）を行い、部分失敗時に他銘柄データを保護。
    - テスト容易性: OpenAI 呼び出し部分を差し替えられるように _call_openai_api を定義。
    - ニュースウィンドウ計算（JST 基準）を提供する `calc_news_window` 実装。

  - 市場レジーム判定 (`src/kabusys/ai/regime_detector.py`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出・LLM スコア化・重み合成・レジーム判定のフローを実装。
    - OpenAI 呼び出しは gpt-4o-mini を使用、リトライ/バックオフ、API エラー時のフォールバック（macro_sentiment = 0.0）。
    - DB（DuckDB）への冪等な書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テスト容易性のため API 呼び出し関数は別実装（news_nlp と共有しない）。

- データ処理 / ETL / カレンダー管理
  - ETL 結果型 (`src/kabusys/data/pipeline.py`, `src/kabusys/data/etl.py`)
    - `ETLResult` dataclass を公開し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を統一フォーマットで保持。
  - カレンダー管理 (`src/kabusys/data/calendar_management.py`)
    - JPX カレンダーを扱うユーティリティ群を実装:
      - 営業日判定: is_trading_day, next_trading_day, prev_trading_day, get_trading_days
      - SQ 日判定: is_sq_day
      - 夜間バッチジョブ: calendar_update_job（J-Quants から差分取得して market_calendar を冪等保存）
    - DB 登録がない場合の曜日ベースフォールバック、部分的な DB 登録に対する整合性確保（DB 値優先・未登録はフォールバック）。
    - 最大探索日数の上限を設定して無限ループを防止。
  - ETL パイプライン（`src/kabusys/data/pipeline.py`）
    - 差分取得・保存（jquants_client の save_* を使用した冪等保存）・品質チェックの設計方針とユーティリティを実装。
    - backfill を考慮した差分範囲算出、品質チェックの記録保持、DB 存在チェックユーティリティ等を提供。

- リサーチ機能（因子計算・特徴量探索）
  - ファクター計算 (`src/kabusys/research/factor_research.py`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）計算: calc_momentum
    - Volatility / Liquidity（20 日 ATR, ATR 比率, 20 日平均売買代金, 出来高比率）計算: calc_volatility
    - Value（PER、ROE）計算: calc_value（raw_financials と prices_daily を組み合わせる）
    - 結果は (date, code) ベースの dict リストで返却。データ不足時は None を利用。
    - DuckDB 上で SQL を活用して効率的に計算。
  - 特徴量探索 (`src/kabusys/research/feature_exploration.py`)
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、入力バリデーション）
    - IC（Information Coefficient）計算: calc_ic（Spearman ρ 実装、最小有効レコード数チェック）
    - ランク計算ユーティリティ: rank（同順位は平均ランク）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）
    - 外部ライブラリに依存せず標準ライブラリのみで実装（pandas 等非依存）。

- パッケージ構成
  - research/__init__.py, ai/__init__.py, data/etl.py などで主要 API を再エクスポートして使いやすく整理。

### 変更 (Changed)
- 初版のため特記事項なし（すべて新規追加）。

### 修正 (Fixed)
- 初版のため特記事項なし。

### セキュリティ (Security)
- OpenAI API キー等の機密情報は環境変数で取得する設計。必須の環境変数が未設定の場合は ValueError を投げて明示的に失敗するため、意図しないキー流出や未設定のまま実行されるリスクを低減。
- .env 自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 注意事項 / 設計上の重要点
- ルックアヘッドバイアス防止:
  - AI / リサーチ系関数は内部で datetime.today() や date.today() を参照せず、必ず caller が渡す target_date を基準に動作するよう設計されています。
- フェイルセーフ設計:
  - 外部 API（OpenAI, J-Quants）や DB 書き込み失敗の際は、致命的例外で全体停止させるのではなく部分失敗を許容・ログ出力しつつ継続する方針が多く採用されています（一部は例外を上位に伝播）。
- DuckDB の互換性考慮:
  - executemany に空リストを渡せないバージョンへの対策（呼び出し前に空チェック）や、list バインドの問題回避のため DELETE を個別に実行する等の実装が含まれます。
- テスト容易性:
  - OpenAI 呼び出し部やその他外部依存箇所を差し替え可能にしており、ユニットテストが書きやすい設計になっています。
- トランザクション安全性:
  - DB 書き込みは BEGIN / COMMIT / ROLLBACK を用いた冪等操作を明示的に行い、例外発生時のロールバック処理とその失敗ログ出力を実装。

### 既知の制限 / 未実装（今後の課題）
- raw_financials に基づく PBR・配当利回り等の一部バリューファクターは未実装（calc_value では PER / ROE のみ実装）。
- 一部ファイル（pipeline モジュール等）における実装の続きを想定する箇所があるため、将来的な補完を予定。
- OpenAI のレスポンスフォーマットやモデルの進化に伴う互換性検証が必要（現行は gpt-4o-mini + JSON mode 前提）。

---

（注）本 CHANGELOG は提供されたソースコードの内容から仕様・設計意図を推測して作成したものであり、実際のコミット履歴や外部変更（テスト、CI、依存パッケージの更新等）は含まれていません。必要であればコミット単位やチケット番号に紐づけたより詳細な履歴への整形も可能です。