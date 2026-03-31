# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、このリポジトリの初期リリースを想定して、ソースコードから推測される機能・設計上の要点をまとめています。

## [Unreleased]
- 特になし

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - public モジュール群をエクスポート: data, strategy, execution, monitoring

- 環境変数 / 設定管理 (`kabusys.config`)
  - プロジェクトルート探索ロジックを実装（.git または pyproject.toml を基準）。
  - .env 自動読み込み実装（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内部のバックスラッシュエスケープ対応
    - クォートなし行のインラインコメント判定（直前が空白またはタブの場合のみ）
    - 無効行・空行・コメント行を無視
  - Settings クラスを追加し、各種必須設定をプロパティ経由で提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証
    - ヘルパープロパティ: is_live / is_paper / is_dev
  - 必須環境変数未設定時に明示的な ValueError を投げる仕組みを導入

- AI モジュール（OpenAI 連携）
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp`)
    - 関数: score_news(conn, target_date, api_key=None)
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して処理
    - 記事集約: news_symbols と raw_news を結合し、銘柄ごとに最新記事を最大件数・文字数でトリム
    - バッチ送信: 1 API コールにつき最大 20 銘柄（_BATCH_SIZE）
    - OpenAI の JSON mode（gpt-4o-mini）を利用して厳密な JSON を期待
    - エラー耐性: 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ
    - レスポンス検証と安全なパース（余計な前後テキストが混入した場合の復元ロジック含む）
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き戻す（DELETE → INSERT）
    - テスト容易性: internal の _call_openai_api を patch して差し替え可能
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - 関数: score_regime(conn, target_date, api_key=None)
    - 指標合成:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）
      - マクロニュースの LLM センチメント（重み 30%）
      - 合成スコアを clip してラベル付け（'bull' / 'neutral' / 'bear'）
    - マクロニュース抽出はキーワードベース（複数キーワードを ILIKE で検索）
    - LLM 呼び出しは gpt-4o-mini を使用、JSON レスポンスを期待
    - API 障害時は macro_sentiment=0.0 としてフェイルセーフ継続
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - テスト容易性: _call_openai_api をモック可能

- データ関連モジュール（DuckDB ベース）
  - ETL パイプライン (`kabusys.data.pipeline`)
    - ETLResult dataclass を公開（etl の実行結果を集約）
    - 差分取得、バックフィル方針、品質チェック（quality モジュール連携）を考慮した設計
    - DB テーブル存在チェック、最大日付取得ユーティリティを提供
  - ETL 公開インターフェース (`kabusys.data.etl`) で ETLResult を再エクスポート
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - market_calendar テーブルを参照して営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB データが無い/未登録の日については曜日ベース（土日を非営業日）でフォールバック
    - next/prev は最大探索日数制限（_MAX_SEARCH_DAYS）を付与して無限ループを防止
    - JPX カレンダーを J-Quants API から差分取得・保存する calendar_update_job を実装
      - バックフィルと健全性チェック（未来日付の異常検出）を実装
  - jquants_client および quality モジュールとの連携（保存・品質検査呼び出し）

- リサーチ（因子計算・特徴量探索）モジュール
  - パブリック API 統合 (`kabusys.research.__init__`)
    - zscore_normalize（data.stats から）
    - calc_momentum, calc_value, calc_volatility（factor_research）
    - calc_forward_returns, calc_ic, factor_summary, rank（feature_exploration）
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - Volatility/Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比
    - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）
    - DuckDB SQL を活用した実装。結果は list[dict] で返却
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman ランク相関）計算（tie の処理を含む）
    - rank（同順位は平均ランク）
    - factor_summary（count/mean/std/min/max/median を算出）
    - 標準ライブラリのみで実装（pandas 等に依存しない）

### Changed
- （初期リリースのため該当なし）

### Fixed
- 安全性・堅牢性向上（実装時点での設計方針）
  - OpenAI 呼び出しでのエラーケース（429、ネットワーク、タイムアウト、5xx）に対する明示的リトライとログ出力を追加し、完全失敗時はフェイルセーフ値を使用して処理継続する設計に。
  - DB 書き込み時のトランザクション保護（BEGIN/COMMIT/ROLLBACK）と ROLLBACK 失敗時の警告ログ出力を実装。
  - DuckDB executemany の空パラメータ制約を回避するガードを追加（空リストを渡さない）。
  - ルックアヘッドバイアス防止: 各モジュールで datetime.today()/date.today() を直接利用しない方針を採用し、ターゲット日を引数として受ける設計に統一。

### Security
- 特になし

---

備考:
- 上記はソースコードから推測される機能・設計上のポイントをまとめた初期 CHANGELOG です。実際のリリースノートとして公開する際は、変更履歴・バグ修正・既知の問題などを運用実績に基づき追記してください。