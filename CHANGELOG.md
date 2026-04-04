# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。日付は推定値です。

## [0.1.0] - 2026-04-04 (初期リリース)
### Added（追加）
- パッケージ全体
  - 初期パッケージ公開。トップレベルのモジュールを __all__ で公開（data, strategy, execution, monitoring）。
  - バージョン情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。

- 環境設定（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に _find_project_root() で探索（実行ディレクトリに依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート処理、インラインコメントの考慮、無効行無視）。
  - 環境変数取得ユーティリティ _require と Settings クラスを追加。J-Quants / kabu / LINE / DB / 監視 / システム関連の設定プロパティを提供。
  - 設定値のバリデーション:
    - KABUSYS_ENV は ("development", "paper_trading", "live") のみ許容。
    - LOG_LEVEL は ("DEBUG","INFO","WARNING","ERROR","CRITICAL") のみ許容。

- AI モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大20銘柄/チャンク）、記事/文字数トリム（最大記事数 10 / 最大文字数 3000）を導入しトークン肥大化を抑制。
    - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx を対象）と指数バックオフを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列チェック、既知コードのみ採用、スコア数値化、±1.0 でクリップ）。
    - DuckDB executemany の空リスト制約に対応した書き込みロジック（DELETE→INSERT、個別 executemany を使用）。
    - テスト容易性のため _call_openai_api を分離し、単体テストでモック可能に。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロキーワードに基づく記事抽出、LLM（gpt-4o-mini, JSON mode）でのセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込みを提供。
    - API 呼び出しのリトライ/フォールバック（全リトライ消費時や解析失敗時は macro_sentiment=0.0 として継続）。
    - OpenAI クライアント呼び出し部分は news_nlp と独立して実装（モジュール結合を低減）。
    - LLM 未設定時は ValueError を送出（api_key 引数または OPENAI_API_KEY 環境変数で指定）。

- データ（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants から差分取得し市場カレンダー market_calendar を冪等保存）。
    - 営業日判定ユーティリティ群を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先し未登録日は曜日ベースでフォールバックするポリシー。探索上限や健全性チェックを導入。
  - ETL / pipeline（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL の取得数/保存数/品質問題/エラーを集約できるように。
    - 差分更新・バックフィル・品質チェック・idempotent 保存の設計方針をコードに反映。
    - jquants_client / quality モジュールと連携してデータ取得・保存・品質検査を行う想定。
  - data パッケージは ETLResult を etl モジュール経由で公開。

- リサーチ（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum, Value, Volatility, Liquidity 等のファクター計算を実装:
      - calc_momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時の None 対応）
      - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率
      - calc_value: PER, ROE（raw_financials と prices_daily を組み合わせて算出）
    - DuckDB ベースの SQL と Python 組合せで高速に計算。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 将来の終値を LEAD で取得して各ホライズンのリターンを計算（horizons バリデーション）。
    - calc_ic: スピアマンランク相関による IC（Information Coefficient）計算（同順位は平均ランク処理）。
    - rank: ランキング（平均ランク、浮動小数の丸めで ties 対応）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージから主要関数を再エクスポート（zscore_normalize など）。

### Changed（変更）
- 全体的な設計方針（ドキュメント化）
  - 重要な設計原則をソース内ドキュメントに明示:
    - ルックアヘッドバイアスを避けるため、datetime.today()/date.today() を内部処理で直接参照しない（target_date ベース設計）。
    - DB 書き込みは冪等化（DELETE→INSERT や ON CONFLICT）を基本とする。
    - OpenAI 呼び出しは JSON mode を使用し、厳密な JSON 出力を期待。ただし応答の頑健性処理を行う。

### Fixed（不具合修正 / 考慮）
- OpenAI SDK の挙動差異に対応:
  - APIError に status_code 属性が存在する場合とない場合の両方を想定して安全に処理。
- DuckDB 実装差異への対応:
  - executemany に空リストを渡せないバージョンを考慮して、空チェックを行う。
- .env パーサでのエスケープ・クォート・コメント処理を堅牢化（複数ケースの取り扱いを改善）。

### Security（セキュリティ）
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で受け取る設計。未設定時は明示的に ValueError を送出して誤設定を防止。
- .env 自動ロード時の保護: OS 環境変数は protected set として .env による上書きを保護（.env.local は上書きだが OS 環境変数は保護される）。

### Known issues / Notes（既知の注意点・今後の TODO）
- jquants_client, quality, monitoring など一部外部連携モジュールは参照されているが、実装はこの差分に含まれていない可能性あり（外部 API クライアント実装を必要とする）。
- news_nlp の JSON mode でも LLM が前後に余計なテキストを混入する可能性があるため、JSON 抽出ロジックを用意しているが万能ではない。応答フォーマットの不一致時は当該チャンクをスキップする設計。
- factor_research の PBR・配当利回り等はいまのバージョンでは未実装（コメントあり）。
- DuckDB の日付型/文字列型差異に注意。内部で日付変換ユーティリティを用意しているが、環境依存の差異が残る可能性あり。
- レート制限や API 側の大幅な仕様変更（OpenAI SDK 等）に対しては将来的に更なる互換対応が必要。

---

（注）この CHANGELOG はコードの内容から仕様・目的を推測して作成しています。実際のリリースノート作成時はリリース日、マイグレーション手順、外部依存関係のバージョンなどを追加してください。