# Changelog

すべての主要な変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョンは 0.1.0（初回リリース）です。

## [Unreleased]

- 今後の変更点を記載します。

## [0.1.0] - 2026-03-26

Initial release.

### Added
- パッケージ基盤
  - パッケージ名: kabusys。トップレベルで data, strategy, execution, monitoring を公開する (src/kabusys/__init__.py)。
  - パッケージバージョンを 0.1.0 に設定。

- 設定管理
  - 環境変数／.env 読込モジュールを追加 (src/kabusys/config.py)。
    - プロジェクトルートを .git または pyproject.toml を起点として自動検出し、.env / .env.local を自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env のパースは export 付き行、シングル／ダブルクォート、エスケープ、インラインコメント等を考慮した堅牢な実装。
    - 既存 OS 環境変数の保護（protected set）および override 制御をサポート。
  - Settings クラスを提供し、以下の設定をプロパティとして取得可能：
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - データベースパス: DUCKDB_PATH / SQLITE_PATH（デフォルトパスあり）
    - システム設定: KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI（自然言語処理）機能
  - ニュースセンチメント・モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、銘柄ごとの sentiment / ai_score を ai_scores テーブルへ書き込み。
    - チャンク処理（デフォルト 20 銘柄/チャンク）、1銘柄あたり最大記事数・文字数でトリム、retry（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
    - レスポンスの厳格なバリデーション（results 配列、型検証、未知コード除外、数値変換、有限値判定）を実施。
    - スコアは ±1.0 にクリップ。API 失敗時はスキップしてフォールバック（フェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。
    - calc_news_window により JST ベースのニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime に変換して利用。
  - 市場レジーム判定モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離 (ma200_ratio) と、ニュース NLP によるマクロセンチメントを重み付け合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - 合成ウェイト: MA 70% / マクロ 30%、スコアはクリップして閾値でラベル付け。
    - prices_daily からのクエリは target_date 未満のみを使用する等、ルックアヘッドバイアス防止設計。
    - OpenAI 呼び出しはリトライ・バックオフと 5xx の扱いを明確化。API 失敗時は macro_sentiment=0.0 で継続。
    - 結果を market_regime テーブルに冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - テスト可能性を考慮し、API 呼び出し部分は差し替え可能。

- データ基盤（Data Platform）
  - ETL パイプライン・ユーティリティ (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（ETL 実行結果の構造化、品質チェック結果とエラーの集約、辞書変換をサポート）。
    - 差分更新、バックフィル、品質チェック、idempotent 保存（jquants_client 経由）を想定した設計。
  - マーケットカレンダー管理モジュール (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを基に営業日判定、次/前営業日の計算、期間内営業日リスト取得、SQ日判定を提供。
    - DB データがない場合は曜日ベースのフォールバック（土日は非営業日）。
    - calendar_update_job を実装し、J-Quants からの差分取得、バックフィル、健全性チェック（将来日付の異常検出）および保存（jquants_client 経由）を行う。
    - _MAX_SEARCH_DAYS 等の探索上限を設け、無限ループを回避。

- Research（リサーチ）モジュール
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離 (ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials と当日株価を用いて PER（EPS が 0 または欠損時は None）、ROE を計算。
    - 実装は DuckDB 上の SQL と Python の組合せ。外部 API には依存しない。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンに対する入力検証あり。
    - calc_ic: スピアマン（ランク）相関に基づく IC 計算。十分なサンプルがない場合は None を返す。
    - rank: 平均ランク方式で同順位に対応するランキング関数（丸めによる ties 誤差を抑制）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージ __all__ で主要関数を再エクスポートし、使いやすく提供。

### Design / Implementation notes
- ルックアヘッドバイアス防止
  - AI / リサーチ関連の関数は datetime.today() / date.today() を内部で参照せず、必ず target_date を引数で受け取ることで過去データのみを使う設計とした。
- フェイルセーフ
  - OpenAI API の失敗やレスポンスパース失敗時は例外で落とさずフォールバック（0.0 やスキップ）して処理継続する設計。DB への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- テスト容易性
  - OpenAI 呼び出し部分はモジュール内のヘルパー関数（_call_openai_api）として切り出しており、unittest.mock.patch 等で差し替え可能。
- DuckDB 互換性
  - executemany に空リストを渡せない制約（DuckDB 0.10）を考慮して、write パスで事前チェックを実施。
- 時間帯取り扱い
  - ニュースウィンドウは JST ベースで定義し、UTC naive datetime に変換して DB 比較に使用（raw_news.datetime は UTC 保存前提）。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 特記事項なし（ただし API キーは環境変数で取り扱い、Settings は必須チェックを行う）。

---

注: この CHANGELOG はリポジトリ内のソースコードから推測して作成しています。各機能の詳細な使用法や API（関数引数・戻り値の仕様、エラー挙動等）は該当モジュールの docstring を参照してください。