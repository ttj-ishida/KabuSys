# Changelog

すべての変更は Keep a Changelog の慣例に従い記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-31

Added
- パッケージ初回リリース。
  - パッケージ名: kabusys、トップレベル __version__ = "0.1.0" を定義。
  - エクスポート済みサブパッケージ: data, strategy, execution, monitoring（パッケージ構成の公開インターフェースを提供）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよびOS環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートは `.git` または `pyproject.toml` を親ディレクトリから探索して特定。
  - .env のパース強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートの中でのバックスラッシュエスケープを正しく処理。
    - インラインコメント・コメント行・無効行の扱いを実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` によって無効化可能。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（必須項目は未設定時に ValueError を送出）。
  - 設定検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の許容値チェックを実装。
  - デフォルトの DB パス（DuckDB/SQLite）を設定するプロパティを実装。
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を使用し、指定ウィンドウ内の記事を銘柄別に集約して OpenAI（gpt-4o-mini）の JSON Mode を用いセンチメントを取得。
  - バッチ処理（デフォルト最大 20 銘柄 / API コール）と、1 銘柄あたりの最大記事数・文字数トリムを実装（トークン肥大化対策）。
  - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx）を実装し、指数バックオフでのリトライを行う。
  - レスポンスのバリデーション実装（JSON 抽出、results リスト、code/score の型チェック、スコアを ±1.0 にクリップ）。
  - 部分成功に対応する DB 書き込み戦略（取得済みコードのみ DELETE → INSERT で置換）を実装。DuckDB 0.10 の executemany 空リスト制約への対応あり。
  - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。
  - ニュースウィンドウ計算ユーティリティ calc_news_window を実装（JST 基準の前日 15:00 ～ 当日 08:30 を UTC naive datetime に変換）。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算・保存する機能を実装。
  - DuckDB 上の prices_daily / raw_news / market_regime を利用し、ルックアヘッドバイアスを避けるため target_date 未満のデータのみ参照。
  - OpenAI API 呼び出し（gpt-4o-mini）に対する耐障害性（リトライ・5xx の扱い・フォールバック macro_sentiment=0.0）を実装。
  - 冪等性を考慮した DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を採用。失敗時は ROLLBACK を試行。
  - マクロニュース抽出用キーワード群を設定し、最大取得件数制限を実装。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の SQL を主体に計算する関数を実装。
    - データ不足時の None 処理やスキャン範囲のバッファ（営業日→カレンダーバッファ）を考慮。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を実装。
    - IC（Spearman の ρ）計算、ランク変換ユーティリティ、ファクター統計サマリー作成機能を実装。
    - pandas 等に依存せず標準ライブラリのみでの実装。
  - research パッケージの __all__ を通じて主要関数を公開。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → market_calendar に冪等保存。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などの営業日判定ユーティリティを実装。DB 登録データ優先、未登録日は曜日ベースでのフォールバックを保持。
    - 最大探索日数や健全性チェック、バックフィル戦略を実装。
  - pipeline:
    - ETLResult データクラスの実装（ETL 実行結果・品質検査結果・エラー情報の保持）。
    - ETL パイプラインの基本設計（差分取得、保存、品質チェック）に必要なユーティリティ関数を実装（_table_exists / _get_max_date など）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
  - jquants_client と quality 連携を想定した設計（実装はクライアント側に委譲）。
- 安全設計・テストしやすさ
  - ルックアヘッドバイアス防止: 主要関数は datetime.today()/date.today() を直接参照せず、target_date を外から与える設計。
  - API 呼び出し点を差し替え可能にしてユニットテストでのモックを容易化。
  - OpenAI SDK の挙動差異（APIError.status_code の有無など）に対する堅牢なハンドリング。

Fixed
- DuckDB の executemany に関する既知制約（空リスト不可）に対応した DB 書き込みコードを導入（部分失敗時に他コードの既存スコアを保護する戦略含む）。

Security
- （今回のリリースではセキュリティ関連の既知修正・脆弱性対応はありません）

Notes / 備考
- OpenAI API（gpt-4o-mini）を利用する機能は API キー（引数 or 環境変数 OPENAI_API_KEY）が必須です。未設定の場合は ValueError を発生させる設計です。
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後の動作検証やユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を活用してください。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充（実行・モニタリング周りの具体的発注ロジック、Slack 連携など）。
- テストカバレッジ強化、CI による安全性チェック。
- J-Quants クライアントの具体実装・エラー処理の追加改善。