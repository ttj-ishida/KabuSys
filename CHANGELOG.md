# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

現在のバージョンはパッケージ定義に合わせて 0.1.0 です。

リンク: 比較やリリースノートへのリンクはこのサンプルでは省略しています。

## [Unreleased]

特になし。

## [0.1.0] - 2026-04-01

初期リリース。以下の主要コンポーネントと機能を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装。__version__ = "0.1.0" を定義し、公開サブパッケージを __all__ で宣言。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を探すため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export 形式、引用符、エスケープ、インラインコメントに対応。
  - Settings クラスで主要設定をプロパティとして提供:
    - J-Quants / kabu ステーション / Slack / DB パス (duckdb/sqlite) / 監視閾値 (CPU/MEM/DISK) / ログレベル / 環境 (development/paper_trading/live) など。
    - 必須設定は未定義時に ValueError を送出する `_require` を利用。
- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄別に最大記事数・文字長でトリムし、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - JSON mode を期待し、レスポンスの厳密なバリデーションを行う（results 配列、code と score、既知コードのみ採用、スコアは ±1 にクリップ）。
    - バッチサイズ、最大記事数、文字数上限、再送戦略（指数バックオフ）などを定義。
    - API 失敗やパース失敗はフェイルセーフで該当チャンクをスキップし、全体処理は継続。
    - 書き込みは部分置換（DELETE → INSERT）で実行し、部分失敗時に他銘柄の既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（unittest.mock.patch を予定）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロニュースは事前定義キーワードでフィルタし、最大記事数を LLM に送信。
    - OpenAI 呼び出しはリトライ・バックオフを実装。API エラー時は macro_sentiment = 0.0 にフォールバック（例外を投げずに継続）。
    - DuckDB への書き込みは冪等に（BEGIN/DELETE/INSERT/COMMIT）行う。
    - ルックアヘッドバイアス対策として date の扱いに注意（datetime.today() を直接参照しない）。
- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - JPX カレンダーの夜間バッチ更新処理（calendar_update_job）を実装。
    - market_calendar を利用した is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未登録の場合は曜日ベース（土日除外）でフォールバック。
    - 更新処理はバックフィルや健全性チェック（未来日付の異常検出）を行い、J-Quants クライアント経由で差分取得・保存。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開し、ETL の実行結果（取得数・保存数・品質問題・エラー一覧）を表現。
    - データ取得差分処理、idempotent な保存（ON CONFLICT DO UPDATE）や品質チェック（quality モジュール連携）に対応する設計。
- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum（1M/3M/6M）、200 日 MA 乖離、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比）などを DuckDB SQL を用いて計算する関数を実装。
    - raw_financials を参照して PER/ROE を計算するバリューファクター calc_value を実装（EPS が 0/欠損なら None）。
    - 計算結果は (date, code) をキーとする dict のリストで返す。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算 (calc_forward_returns): 指定 horizon の将来終値リードを利用してリターンを計算。
    - IC（Information Coefficient）計算 (calc_ic): スピアマンランク相関を実装（ties の扱い、3 件未満は None）。
    - rank / factor_summary: ランク変換と基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで提供。
  - 研究用ユーティリティ zscore_normalize を data.stats から再エクスポート。
- 各所での設計方針・品質
  - DuckDB を主要ストレージとして想定し、SQL と軽量 Python ロジックで処理を完結。
  - ルックアヘッドバイアス防止のため、日付処理は明示的に target_date を受け取る設計。
  - OpenAI への呼び出しはリトライ、5xx 判定、429/ネットワーク断対応のバックオフを実装。
  - テスト容易性のため、外部呼び出し（OpenAI など）を差し替えやすいように内部関数設計（モック対象）を採用。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

---

注記（設計上の重要点、ユーザーへの注意）
- 環境変数未設定時に必須値を参照すると ValueError が発生します（Settings の必須プロパティ）。
- OpenAI API キーは api_key 引数で注入可能（テストや実行時の柔軟性のため）。api_key 未指定の場合、環境変数 OPENAI_API_KEY を使用します。
- DuckDB による executemany の仕様（空リストは不可）を考慮した実装になっています。
- JSON Mode を使った LLM 出力を前提としていますが、外部 API の挙動により余分なテキストが混入する場合があるため、レスポンスパース時に最外側の JSON オブジェクト抽出ロジックを備えています。
- ルックアヘッドバイアス（未来データ利用）を防ぐため、各スコア計算関数は target_date を明示的に受け取ります。テストや運用時は target_date を適切に与えてください。

将来のリリースでは、モジュールの細分化、追加テストカバレッジ、外部サービスの抽象化（HTTP クライアントの注入）や監視・運用向け機能の拡張を予定しています。