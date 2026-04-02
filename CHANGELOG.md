# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従い、Semantic Versioning を採用しています。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: 修正
- Deprecated / Removed / Security: 必要に応じて記載

## [0.1.0] - 2026-04-02

### Added
- パッケージ基盤
  - 初期リリースとして kabusys パッケージを追加。
  - パッケージバージョンは `__version__ = "0.1.0"`。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
    - プロジェクトルート検出: `.git` または `pyproject.toml` を基準にパッケージ配置に依存しない探索を実装。
  - .env パーサー実装:
    - `export KEY=val` 形式の対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープに対応。
    - クォート無しの場合のインラインコメント判定（直前が空白/タブの `#` をコメント扱い）。
  - Settings クラスでアプリケーション設定をプロパティとして提供。
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / システム設定（env・log_level）などを取得。
    - 必須値取得時の未設定検出で `ValueError` を送出する `_require` を使用。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証実装（許可値集合に基づくバリデーション）。
    - デフォルト DB パス: `DUCKDB_PATH = data/kabusys.duckdb`, `SQLITE_PATH = data/monitoring.db`。
    - PID ファイル・CPU/MEM/DISK 閾値のプロパティを提供。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を算出。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたり記事数・文字数制限、JSON レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - Windows/Unix 環境差や DuckDB の制約に配慮し、書き込み時は部分的な DELETE → INSERT で冪等性を確保。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（unittest.mock.patch で _call_openai_api をモック可）。
    - タイムウィンドウ計算ユーティリティ `calc_news_window(target_date)` を公開。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（70% 重み）と、マクロニュースに対する LLM センチメント（30% 重み）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）、JSON パース、リトライロジック、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアスを避ける設計（datetime.today() を直接参照せず、DB クエリで date < target_date 等の排他条件を採用）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理：market_calendar テーブルを用いた営業日判定・次/前営業日計算・期間内営業日列挙、SQ 判定などを実装。
    - market_calendar が未登録または欠損時は曜日ベース（平日）でフォールバックする一貫した挙動を提供。
    - 夜間バッチジョブ `calendar_update_job` を実装し、J-Quants API から差分取得 → 冪等保存（バックフィル・健全性チェックを含む）を行う。
  - pipeline / ETL:
    - ETL のインターフェースと結果を表す `ETLResult` データクラスを実装（取得数・保存数・品質問題・エラー情報の集約）。
    - 差分更新・バックフィル・品質チェック方針を想定しての設計（品質チェックで致命的な問題があっても全件収集して呼び出し元で判断）。
    - `kabusys.data.etl` から `ETLResult` を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research:
    - Momentum / Value / Volatility / Liquidity 等のファクター計算機能を追加:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
      - calc_volatility: 20 日 ATR（atr_20）、atr_pct、avg_turnover、volume_ratio
      - calc_value: raw_financials から EPS/ROE を組み合わせた PER, ROE の算出
    - DuckDB を利用した SQL ベースの計算で、価格データと財務データのみ参照する安全設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得するクエリ実装（パフォーマンスのためスキャン範囲を制限）。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）計算を実装。最小有効サンプル数チェックを含む。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクを返すランク変換ユーティリティ（丸めで ties 検出漏れに対処）。

- テスト・拡張性設計
  - OpenAI 呼び出し部分はモジュール内で独立しており、テスト時に差し替え可能。
  - API キー（OPENAI_API_KEY）は関数引数経由で注入できる設計（テスト容易性）。

- ロギング・トランザクション制御
  - 各所に詳細な logger.info / logger.warning / logger.exception の出力を追加。
  - DB 書き込みは BEGIN/COMMIT/ROLLBACK を明示して冪等性と整合性を担保。

### Changed
- 初回リリースのため該当なし（新規追加が中心）。

### Fixed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーは環境変数または明示的な引数でのみ解決され、未設定時は ValueError を送出して誤動作を防止。
- .env 読み込み時に OS 環境変数を保護する仕組み（既存の OS 環境変数を protected として扱い上書きを制御）。

### Notes / Implementation details（設計上の重要事項）
- ルックアヘッドバイアス対策として、日付処理はすべて target_date ベースで行い、datetime.today()/date.today() の乱用を避ける実装方針を採用。
- 外部 API 呼び出しは失敗時フェイルセーフ（スコア 0 やチャンクスキップ）で継続し、システム全体の耐障害性を重視。
- DuckDB の制約（executemany に空リストを渡せない等）を考慮した実装を行っている。
- いくつかの外部モジュール（例: kabusys.data.jquants_client）を参照しており、実動作時はそれらの実装が必要。

---

将来的なリリースでは、以下の点を予定／検討:
- AI モデルの切替やパラメータチューニングを容易にする設定の追加。
- ETL ワークフローの CLI / スケジューラ統合。
- テストカバレッジ強化（ユニット・統合テスト）。
- 監視/アラート連携（Slack通知等）の実装拡張。

（以上）