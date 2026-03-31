# CHANGELOG

すべての重要な変更点を記載します。フォーマットは「Keep a Changelog」に準拠します。

全般方針：
- ルックアヘッドバイアス防止のため、各処理は内部で datetime.today()/date.today() を直接参照せず、対象日（target_date）を明示的に受け取る設計になっています。
- DuckDB を主要なローカルデータストアとして利用し、DB 書き込みは冪等性（BEGIN / DELETE / INSERT / COMMIT や ON CONFLICT）を意識して実装されています。
- 外部 API（OpenAI / J-Quants 等）呼び出しは耐障害性（リトライ、フォールバック、エラーハンドリング）を考慮しています。

## [0.1.0] - 2026-03-31
### Added
- パッケージ初期リリース（kabusys v0.1.0）。
- パッケージ公開インターフェースを追加
  - src/kabusys/__init__.py にて version と主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 設定・環境変数管理モジュールを追加（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を __file__ を起点に自動検出し、.env/.env.local を自動読み込みする仕組みを実装。
  - .env パーサ実装：コメント行・export プレフィックス、シングル/ダブルクォート対応、バックスラッシュエスケープ、インラインコメントの扱いを考慮。
  - OS 環境変数保護機構：.env ファイル読み込み時に既存の OS 環境変数を保護する protected set を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - Settings クラス提供：必須環境変数取得（_require）、各種設定プロパティ（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境モード / ログレベル判定等）を用意。値検証（KABUSYS_ENV / LOG_LEVEL の正当性チェック）を実装。
- AI 関連モジュールを追加（src/kabusys/ai）
  - news_nlp.score_news
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込み。
    - バッチ（最大 20 銘柄）での送信、1 銘柄あたりの記事数・文字数制限（トリム）、JSON Mode 応答のバリデーション、スコア ±1.0 クリップ、部分書き換え（DELETE→INSERT）による部分失敗耐性を実装。
    - リトライ方針：429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他エラーはスキップし続行。テストで差し替え可能な _call_openai_api フックを用意。
    - calc_news_window ユーティリティを追加（JST→UTC 変換でニュース収集ウィンドウを計算）。
  - regime_detector.score_regime
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（マクロキーワードリスト）→ LLM 評価（gpt-4o-mini、JSON 出力期待）→ スコア合成。API 失敗時は macro_sentiment=0.0 のフェイルセーフを採用。
    - OpenAI クライアント呼び出しやリトライの実装を備え、テスト容易性のため内部呼び出しを独立実装。
- Data（データプラットフォーム）モジュールを追加（src/kabusys/data）
  - calendar_management
    - market_calendar を用いた営業日判定・前後営業日探索・期間内営業日リスト取得・SQ 判定ロジックを実装。
    - market_calendar が未登録または欠損の場合の曜日ベースフォールバック実装。
    - calendar_update_job 実装：J-Quants から差分取得して market_calendar を冪等に更新。バックフィル・健全性チェック（将来日付異常検知）を実装。
  - pipeline / ETLResult（etl.py / pipeline.py）
    - ETLResult dataclass を公開（ETL 実行結果の集約、品質問題・エラーの集計、辞書化ユーティリティ）。
    - ETL パイプラインの設計に沿ったユーティリティ（差分更新、バックフィル、品質チェックのフック）を実装（jquants_client / quality と連携する想定）。
  - etl 再エクスポート（src/kabusys/data/etl.py）。
- Research（研究用分析機能）を追加（src/kabusys/research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比を計算。
    - calc_value: raw_financials から最新財務を結合して PER / ROE を計算。
    - DuckDB SQL ベースの実装で外部 API を呼ばない設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得する汎用実装。
    - calc_ic: Spearman ランク相関（Information Coefficient）計算。データ不足（有効レコード < 3）時は None。
    - rank: 同順位は平均ランクにするランク関数（丸めで ties 検出漏れを防止）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。
  - research パッケージ公開（主要関数を __init__ で再エクスポート）。
- その他ユーティリティ
  - data パッケージの jquants_client / quality 等との連携を想定したインターフェース設計。
  - DuckDB に関する互換性考慮（executemany が空リストを受け付けない問題へのガード）が多数箇所に反映。

### Changed
- （初回リリースのため該当なし）

### Fixed / Robustness
- OpenAI / 外部 API 呼び出しでの堅牢性向上
  - 429/ネットワーク断/タイムアウト/5xx に対するリトライと指数バックオフを各所に実装（news_nlp, regime_detector）。
  - API レスポンスの JSON パースエラーや予期しない形式に対して、安全にフォールバック（スコア=0.0 やスキップ）する処理を追加。
- DuckDB 書き込みの冪等化とエラーハンドリング
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を用いた安全な書き込み。
  - ROLLBACK が失敗した場合のログ出力保護。
  - executemany へ空リストを渡さないガード（DuckDB 0.10 互換性のため）。
- .env パーサの堅牢化
  - export プレフィックス、クォート中のエスケープ、インラインコメント処理などを考慮。

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の必須チェック（OpenAI API キー等）で未設定時に明確な例外（ValueError）を投げるようにし、誤設定を早期に検出。
- OS 環境変数を .env で不意に上書きしない保護ロジックを導入。

### Notes / Design Decisions
- ルックアヘッドバイアス回避のため、すべてのデータ処理は target_date を明示的に受け取り、内部で現在日付を参照しない方針を採用しています（テスト可能性と研究再現性の向上）。
- OpenAI 呼び出しはテスト時にモック差し替えを容易にするため、各モジュールにて _call_openai_api を分離しています（モジュール間でプライベート関数を共有しない）。
- DB によるカレンダー情報が不完全な場合でも、曜日ベースのフォールバックを行い処理継続を保証します。
- J-Quants / kabu 系のクライアント実装は外部モジュール（jquants_client 等）に委譲するインターフェース設計としています。

---
今後の予定（例）
- strategy / execution / monitoring の具体的な実装拡張（注文発行ロジック、監視アラートの実装）。
- テストカバレッジ強化（外部 API モック、DuckDB を利用した統合テスト）。
- ドキュメント（StrategyModel.md / DataPlatform.md 等）に対応した詳細な運用手順書の追加。