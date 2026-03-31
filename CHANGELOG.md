# Changelog

全ての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、この changelog は提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

- なし（現時点での最新安定実装は 0.1.0）

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装。

### Added
- パッケージ初期化
  - パッケージメタ情報を定義（src/kabusys/__init__.py）。
  - __version__ = "0.1.0"、公開モジュール一覧を __all__ に定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート（テスト用途）。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行い、CWD に依存しない。
  - .env パーサは export 構文、クォート文字列、エスケープ、コメント扱い（'#'）などのケースに対応。
  - Settings クラスを提供し、必須変数のチェック（_require）とデフォルト値（KABUSYS_ENV, LOG_LEVEL, DB パス等）を実装。
  - 有効値検証（KABUSYS_ENV, LOG_LEVEL）のバリデーションを実施。

- データプラットフォーム（src/kabusys/data/*）
  - ETL 基盤
    - ETLResult データクラスを公開（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）。
    - 差分取得・バックフィル・品質チェックを想定した設計（J-Quants クライアント経由での差分取得、保存は idempotent）。
    - DuckDB を前提とした最大日付取得やテーブル存在チェック等のユーティリティを実装。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定ロジックを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB 登録が無い日や NULL 値に対する曜日ベースのフォールバックを採用。
      - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを防止。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants から差分取得して保存、バックフィル対応、健全性チェック）。

- 研究・ファクター計算（src/kabusys/research/*）
  - ファクター計算群（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m / mom_3m / mom_6m および ma200_dev（200日移動平均乖離率）。
    - ボラティリティ/流動性: 20日 ATR（atr_20）、atr_pct、avg_turnover、volume_ratio。
    - バリュー: PER（price / EPS、EPS=0/未設定時は None）、ROE（raw_financials から取得）。
    - DuckDB のウィンドウ関数を活用し、営業日スキャン範囲・データ不足時の None 扱い等を実装。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証、1クエリで複数ホライズン取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ 相当のランク相関、3件未満は None）。
    - ランク関数 rank（同順位は平均ランク、丸めによる ties 対策）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
  - research パッケージ公開 API を整備（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- AI（自然言語処理）モジュール（src/kabusys/ai/*）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）に JSON モードでバッチ評価を依頼して ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済み）を対象。
    - バッチサイズ、記事数・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンス検証（JSON 抽出、results 配列、code/score の妥当性、数値化、±1.0 クリップ）。
    - 部分失敗時に既存スコアを保護するため、取得したコードのみ DELETE → INSERT（冪等性）で書き換え。
    - テスト容易性のため OpenAI 呼び出し箇所を patch で差し替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動型）の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で regime（bull/neutral/bear）を判定。
    - prices_daily と raw_news からデータ取得、calc_news_window を利用したウィンドウ計算、OpenAI（gpt-4o-mini）によるマクロセンチメント評価を実装。
    - レジームスコア合成 formula: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）、例外時は ROLLBACK を試行。
    - OpenAI 呼び出しのリトライ/バックオフ/エラーハンドリングを実装。

- 公開 API のテストフック・堅牢化
  - OpenAI 呼び出し箇所を個別関数として定義し、ユニットテストで差し替え（patch）可能に実装。
  - API 呼び出し失敗やレスポンスパース失敗はデフォルト値（0.0 やスキップ）で継続するフェイルセーフ設計。
  - DuckDB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で安全に処理し、ROLLBACK 失敗時は警告ログを出力。

- ロギング・バリデーション
  - 各モジュールで適切な情報ログ・警告ログを追加（データ不足、API失敗、パースエラー、異常なカレンダー日付など）。
  - 入力パラメータ（horizons、KABUSYS_ENV、LOG_LEVEL、APIキー存在など）のバリデーションを実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- DuckDB を分析ストアとして利用する前提で SQL を多用（ウィンドウ関数、LEAD/LAG、ROW_NUMBER 等）。
- 日付の扱いはすべて date / naive datetime（UTC 想定の DB 値）で統一し、時間帯混入を防止。
- ルックアヘッドバイアス防止のため、関数は内部で datetime.today()/date.today() に依存しない設計（target_date 引数を必須にする）。
- OpenAI モデルは gpt-4o-mini を想定している（JSON Mode を利用）。
- J-Quants 関連クライアント呼び出し（jquants_client）はインターフェース設計を仮定して組み込み（fetch/save 関数を想定）。

### Security
- API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY からも解決。未設定時には ValueError を投げて明示。

---

参照: この CHANGELOG は提供されたソースコードから推測して作成したものであり、実際のリリースノートや履歴は開発履歴（コミットログ等）に基づいて調整してください。必要であれば、各モジュールごとの細かな変更点や既知の問題点（TODO/ISSUES）を追加作成できます。