# Changelog

すべての非互換な変更はセクション「Unreleased」または各バージョンの見出しに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

テンプレートのバージョン: 0.1.0

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-31

### Added
- 初期リリース: kabusys パッケージを追加。
  - パッケージ全体のバージョニングは `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` を設定。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - プロジェクトルート検出（`.git` または `pyproject.toml` を探索）により、CWD に依存しない自動読み込みを実現。
  - .env パーサを実装（`export KEY=val` 形式・クォート・エスケープ・インラインコメント対応）。
  - 環境変数の保護（既存 OS 環境変数を `protected` として上書き制御）。
  - `Settings` クラスを提供し、必須項目（J-Quants / kabu / Slack トークン等）の取得と検証 (`_require`) を実装。
  - 設定値の簡易検証: `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL`（DEBUG/INFO/...）のバリデーション。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメントを算出して `ai_scores` に書き込むバッチ処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に計算する `calc_news_window` を実装。
    - バッチ処理（デフォルト 20 銘柄/回）・1 銘柄あたり記事数/文字数制限（トリミング）でトークン肥大化を抑制。
    - API 呼び出しに対するリトライ／エクスポネンシャルバックオフ（429/ネットワーク断/タイムアウト/5xx を想定）。
    - レスポンス検証ロジック（JSON 抽出、results の構造/型チェック、未知コードの無視、スコアの ±1.0 クリップ）。
    - DuckDB への冪等化された書き込み（DELETE → INSERT、部分失敗時は既存スコア保護）。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（内部 `_call_openai_api` をパッチ可能に実装）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - マクロ記事抽出のためのキーワードリストを内包。最大記事数やスケール係数等は定数化。
    - OpenAI 呼び出し・リトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - 計算結果を `market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策（target_date 未満のデータのみ使用、datetime.today() 非参照）。

- Data モジュール（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants API から差分取得、ON CONFLICT 相当で保存）。
    - 営業日判定ユーティリティ：`is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。
    - DB データがない場合の曜日ベースのフォールバックや、データ不整合時の健全性チェック（最大探索日数制限）を実装。
    - market_calendar がまばらにしか存在しない場合でも一貫した判定を返す設計。

  - ETL / パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - 差分取得・保存・品質チェックのためのパイプラインの骨組みを追加。
    - ETL 実行結果を格納する `ETLResult` dataclass を公開（`to_dict` により品質問題をシリアライズ）。
    - テーブル最終日取得・存在チェック等のユーティリティを提供。
    - デフォルトのバックフィルやカレンダー先読み等の設定を組み込み、API 後出し修正に対応。

- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR / 相対 ATR / 平均売買代金 / 出来高比率）、Value（PER / ROE）を計算する関数を実装。
    - DuckDB 上の SQL を用いて、業務上の営業日バッファを考慮したスキャン範囲で算出。
    - データ不足時の None ハンドリングやログ出力を実装。

  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（`calc_forward_returns`）、IC（Spearman のランク相関）計算（`calc_ic`）、ランク変換（`rank`）、ファクター統計サマリー（`factor_summary`）を実装。
    - 外部依存を持たず標準ライブラリと DuckDB のみで実装し、ルックアヘッドバイアス回避を明示。

- 共通・ユーティリティ
  - DuckDB を中心としたデータ操作に統一（関数引数で DuckDB 接続を受け取る設計）。
  - ロギングを各モジュールへ導入し、情報・警告・例外の記録を強化。
  - OpenAI クライアント（OpenAI SDK）を利用する箇所は、API エラー／ステータスコード判定を安全に扱う実装。

### Changed
- （該当なし、初回リリース）

### Fixed
- （該当なし、初回リリース）

### Security
- 機密情報（API キー等）は Settings 経由で明示的に要求し、未設定時は ValueError を送出することで誤動作を防止。

---

Notes / 設計上の重要ポイント:
- ルックアヘッドバイアス回避: 多くのアルゴリズムで内部的に datetime.today() / date.today() を直接参照せず、呼び出し側が `target_date` を与える設計を徹底。
- Idempotency（冪等性）: DB 書き込みは DELETE → INSERT（トランザクション内）などで既存データの上書きを安全に行う。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）障害時は例外で停止させる箇所と、ロギングしてフォールバック値で継続する箇所を分離。
- テスト容易性: OpenAI 呼び出し等は内部関数をパッチ可能にし、ユニットテストでの差し替えを想定。

必要であれば、各モジュールごとのAPI使用例・期待されるDBスキーマの概要やマイグレーション手順、主要設定項目のドキュメント化を追補します。どの情報が欲しいか教えてください。