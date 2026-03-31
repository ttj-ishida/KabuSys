# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般方針:
- バージョンは semantic versioning に従います。
- 日付はリリース日を示します。
- 変更点は実装されたコードから推測して記載しています。

## [Unreleased]
- （現在のスナップショットは 0.1.0 を初回リリースとして想定しています）

## [0.1.0] - 2026-03-31

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開。__version__ = 0.1.0、主要サブパッケージ（data, research, ai, etc.）の骨組みを追加。

- 環境設定 / config
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード:
    - プロジェクトルート検出: .git または pyproject.toml を起点にプロジェクトルートを解決する機構を導入（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサを独自実装（コメント処理、export での定義、シングル/ダブルクォート内のバックスラッシュエスケープに対応）。
  - 環境変数取得用ユーティリティ _require を追加（未設定時は ValueError を投げる）。
  - 設定プロパティを公開:
    - J-Quants, kabuステーション, Slack, DB（duckdb/sqlite）パス、監視閾値（CPU/メモリ/ディスク）、ログレベル/環境（development/paper_trading/live）など。

- AI モジュール
  - ニュースセンチメントスコアリング（news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini, JSON Mode）で各銘柄のセンチメントを算出。
    - チャンク処理（最大 20 銘柄 / API コール）、1銘柄あたりの最大記事件数・文字数トリム、スコアを ±1.0 でクリップ。
    - 再試行ロジック: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフと最大試行回数管理。
    - レスポンスの堅牢なバリデーション（JSON 解析補正、results フォーマットチェック、未知コードの無視、数値チェック）。
    - スコア書き込みは冪等（DELETE → INSERT）で実行、部分失敗時にも既存の他銘柄スコアを保護。
    - テスト容易性: OpenAI 呼び出し箇所を差し替え可能（_call_openai_api をモック可）。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロセンチメントはニュースタイトルを抽出して LLM に評価させる（最大 20 件）。
    - LLM 呼び出しに対する再試行、API 失敗時のフォールバック（macro_sentiment=0.0）、JSON パースエラーのハンドリングを実装。
    - DB 書き込みはトランザクションで冪等に実行（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- Data モジュール
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルをベースに営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録がない場合は曜日ベースでフォールバック（土日非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル、健全性チェック（将来日付の異常検知）を実装。
  - ETL パイプライン（pipeline / etl）
    - ETLResult dataclass を公開し、ETL 実行結果（取得/保存件数、品質問題、エラー）を集約する仕組みを追加。
    - 差分取得、バックフィル、品質チェック（quality モジュールと連携）などの設計を導入。
    - jquants_client 経由での取得 / 保存を想定したフローを実装（保存は冪等性を重視）。
  - etl の公開インターフェースを etl モジュールで再エクスポート（ETLResult）。

- Research モジュール
  - factor_research
    - Momentum ファクター（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR、相対 ATR）、Liquidity（20日平均売買代金、出来高比率）、Value（PER, ROE）を計算する関数を追加（prices_daily / raw_financials を使用）。
    - DuckDB 上の SQL を多用して効率的に計算。データ不足時の None ハンドリング。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns: 複数ホライズン一括取得）、IC（Spearman ランク相関）計算、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリで実装。
  - research パッケージの便利関数を __all__ で公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security / Hardening
- .env の自動読み込みで OS 環境変数を保護するため protected キーセットを導入し、.env.local の override を OS 環境変数でブロック。
- OpenAI 呼び出しはタイムアウト/再試行/5xx を考慮しフェイルセーフ（API 失敗 → スコア 0.0 / スキップ）でシステムの停止を防止。

### Internal / Design notes
- 全 AI/リサーチ処理は「ルックアヘッドバイアス防止」の方針に従い、datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
- DuckDB を主要なデータ格納・クエリ基盤として利用。SQL 内ウィンドウ関数や LEAD/LAG を多用して計算を行う。
- OpenAI 呼び出し箇所はテスト容易性のため差し替え可能（ユニットテストでのモックを想定）。
- ai/news_nlp と ai/regime_detector では内部の _call_openai_api を意図的に共有していない（モジュール結合を避ける設計）。

### Known issues / Limitations
- calc_value: PBR や配当利回りは現時点で未実装（コメントに明記）。
- news_nlp / regime_detector:
  - LLM 出力に依存するため、モデル応答の品質がスコア結果に影響する。レスポンス検証やフォールバックは実装済みだが、エッジケースの振る舞いに注意が必要。
- pipeline モジュールの末尾に断片的なコード（例: return date.fro のような未完の記述）が見られ、そこは実装途中またはコピー時の切れ目と思われる。実際の運用前に pipeline の残り実装・テストが必要。
- data/__init__.py は暫定的に空（将来的にクライアント等の公開を想定）。
- 本リリースでは実際の発注・execution・monitoring の実装（外部 API 呼び出しによる注文発行など）は含まれておらず、主にデータ処理・研究・AI スコアリングの基盤を提供。

---

将来的なリリースでは、以下を想定しています:
- pipeline の完成・エンドツーエンド ETL の安定化とテスト補強
- 発注実行（execution）・監視（monitoring）機能の追加・統合
- 追加ファクター（PBR・配当利回り等）および品質チェック項目の拡充

（この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は、その実リリース情報に合わせて更新してください。）