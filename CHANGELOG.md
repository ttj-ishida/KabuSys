# CHANGELOG

すべての変更は Keep a Changelog の慣例に従います。
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]
- (なし)

## [0.1.0] - 2026-04-04
初回リリース。

### Added
- パッケージ基本構成
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - 公開モジュールのエクスポートを定義（data, strategy, execution, monitoring）。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env/.env.local ファイル自動読み込み機能を実装（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - .env パーサー実装（コメント・export プレフィックス・シングル／ダブルクォート・エスケープ処理を考慮）。
  - protected（OS環境変数保護）と override による上書き制御。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム環境 (development/paper_trading/live) 等のプロパティを提供。
  - 環境変数未設定時は明示的に ValueError を投げる必須取得メソッドを追加。

- AI モジュール
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを取得して ai_scores テーブルへ書き込む処理を実装。
    - 処理仕様：
      - ニュース収集ウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 相当の UTC 範囲）。
      - 1チャンク最大 20 銘柄（_BATCH_SIZE=20）でバッチ送信、1銘柄あたり記事数・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、その他エラーはスキップして継続（フェイルセーフ）。
      - レスポンスのバリデーション実装（JSON 抽出・results リスト検査・コード照合・数値検証）。
      - スコアは ±1.0 にクリップ。
      - DuckDB への書き込みは部分置換（DELETE → INSERT）で冪等性と部分失敗時の保護を実現。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で regime_score/label を生成し market_regime テーブルへ冪等書き込み。
    - LLM（gpt-4o-mini）呼び出しのリトライ／バックオフ、API エラー時は macro_sentiment=0.0 で継続するフェイルセーフを実装。
    - ルックアヘッドバイアス対策（target_date 未満のみ参照）等の設計方針を採用。

- リサーチ機能（src/kabusys/research/*.py）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR / 相対 ATR）、Value（PER, ROE）および流動性指標（20 日平均売買代金 / 出来高比）を DuckDB を用いて計算する関数を追加（calc_momentum / calc_volatility / calc_value）。
    - 欠損やデータ不足時の振る舞い（None を返す、行数チェック）を明確化。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）の fwd_* を生成。
    - IC（Information Coefficient）計算（calc_ic）：Spearman（ランク相関）でファクターの有効性を評価、十分なサンプルがない場合は None を返す。
    - ランク関数（rank）：同順位は平均ランクに対応。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。
  - research パッケージの __init__ で主要関数を再エクスポート。

- データ基盤（src/kabusys/data/*.py）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を扱うユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先、未登録日は曜日ベースのフォールバックを行う一貫したロジック。
    - calendar_update_job を実装し J-Quants クライアントからの差分取得 → 保存（バックフィル・健全性チェック含む）を行う。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult dataclass を公開（etl.py は pipeline.ETLResult を再エクスポート）。
    - 差分更新・保存（idempotent save）・品質チェックの取り扱い方針（品質エラーは収集し呼び出し元に委ねる）を実装。
    - DuckDB の存在チェックや最大日付取得等のユーティリティを実装。

- パッケージの小さな公開周り
  - ai パッケージの __init__ で score_news を公開。
  - research パッケージで各種関数を再エクスポート。
  - data.etl で ETLResult を公開。

### Changed
- 初回リリースのため変更履歴はなし（新規実装）。

### Fixed
- 初回リリースのため修正履歴はなし。

### Notes / 設計上の重要事項
- ルックアヘッドバイアス防止：AI / リサーチ機能は内部で datetime.today() / date.today() を参照せず、必ず caller が与える target_date を基準にデータを選定します。
- フェイルセーフ：外部 API（OpenAI, J-Quants など）の失敗は基本的に局所的に処理して続行する設計です（例: マクロセンチメント失敗時は 0.0、ニューススコア失敗時はそのチャンクをスキップ）。
- DuckDB 書き込みは冪等性を意識（DELETE → INSERT や ON CONFLICT 相当の扱い）して実装。
- OpenAI 呼び出しは JSON Mode を想定した厳密なパースとバリデーションを行う。
- .env パースは実用上の多様なケース（export キー、クォート、エスケープ、インラインコメント）に対応。

### Known limitations / TODO（今後の改善候補）
- strategy / execution / monitoring 等の実行・発注関連モジュールはこのリリースでは実装の痕跡があるが（__all__ に含まれる）、本稿のコードベースには含まれていない。実運用の前に発注ロジック・監視ロジックの実装と十分なテストが必要。
- 一部の DuckDB バインド互換性（executemany に対する空リストの取り扱い等）への対応が明記されているため、DuckDB の将来バージョンによる動作変化に注意が必要。
- OpenAI SDK のバージョン差異に対する互換性考慮（例: APIError の status_code）が実装されているが、SDK の大幅な仕様変更時には追加対応が必要。

---

今後のリリースでは、運用監視・発注経路・回帰テスト・CI の充実、性能改善（大規模ニュース処理時のメモリ・レイテンシ最適化）などを予定しています。