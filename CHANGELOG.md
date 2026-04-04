CHANGELOG
=========

すべての変更は Keep a Changelog に準拠して記載しています。  
このプロジェクトはセマンティックバージョニングに従います（https://semver.org/）。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージのバージョンを追加: `kabusys.__version__ = "0.1.0"`。
  - 主要サブパッケージを公開: `data`, `strategy`, `execution`, `monitoring` を `__all__` に設定。

- 環境設定 / 初期化（kabusys.config）
  - .env ファイルと OS 環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を上位ディレクトリから探索して特定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化対応（テスト用）。
  - .env ファイルの柔軟なパース実装（コメント、export プレフィックス、シングル/ダブルクォートやエスケープを考慮）。
  - 環境変数取得ユーティリティ `Settings` を提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログレベル等）。
    - 必須環境変数未設定時は明示的に ValueError を返す `_require` を実装。
    - `env`（development/paper_trading/live）や `log_level` のバリデーション実装。
    - ファイルパス設定は `Path.expanduser()` を用いて扱う。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄別に記事を結合し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを付与。
    - バッチ処理: 最大 20 銘柄単位でのチャンク化、1 銘柄あたりの記事件数・文字数上限を設定（トークン肥大化対策）。
    - 再試行（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実装。その他のエラーはスキップしてフェイルセーフに継続。
    - レスポンス検証ロジックを実装（JSON 抽出、results リスト検査、コード照合、数値検証、±1.0 でクリップ）。
    - DuckDB へは idempotent に書き込む（DELETE → INSERT、部分失敗時は既存スコアを保護）。
    - エクスポート API: `score_news(conn, target_date, api_key=None)`。
    - ニュースウィンドウ計算ユーティリティ `calc_news_window(target_date)`（JST 前日 15:00 〜 当日 08:30 を UTC に変換して返す）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントは OpenAI（gpt-4o-mini）へタイトルリストを送り JSON を期待して取得。
    - API 再試行と 5xx の扱い、API 失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - エクスポート API: `score_regime(conn, target_date, api_key=None)`。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline / etl）
    - 差分取得・バックフィル・品質チェックを想定した ETL 結果表現 `ETLResult` を公開。
    - DuckDB 操作ユーティリティ（テーブル存在確認、最大日付取得等）とエラー / 品質問題の収集方針を定義。
    - ETL 設計方針: idempotent 保存、バックフィル、品質チェックは収集継続（Fail-Fast しない）。
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job(conn, lookahead_days=...)` を実装（J-Quants クライアント経由）。
    - 営業日判定ユーティリティを提供:
      - is_trading_day(conn, d)
      - next_trading_day(conn, d)
      - prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
      - is_sq_day(conn, d)
    - DB 未取得時は曜日ベースのフォールバック（土日を非営業日扱い）。DB 登録ありの場合は DB 値優先。
    - 最大探索日数など安全策（サニティチェック、バックフィル日数、探索上限）を実装。
  - jquants_client 経由のデータ取得/保存を想定したインタフェースを準備（外部クライアントへの依存を分離）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する `calc_momentum(conn, target_date)` を実装。データ不足時の None 処理。
    - Volatility / Liquidity: 20 日 ATR・相対 ATR、20 日平均売買代金、出来高比率を計算する `calc_volatility(conn, target_date)` を実装。true_range の NULL 伝播に注意して計算。
    - Value: EPS / ROE から PER・ROE を計算する `calc_value(conn, target_date)` を実装（最新財務レコードの取得ロジックを含む）。
    - DuckDB を利用した SQL ベース実装、外部 API へはアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト [1,5,21]）を実装。ホライズンバリデーションあり。
    - IC 計算: スピアマンのランク相関を計算する `calc_ic(factor_records, forward_records, factor_col, return_col)` を実装（不足レコード検出で None を返す）。
    - ランキングユーティリティ: `rank(values)`（同順位は平均ランク）。
    - ファクター統計サマリー: `factor_summary(records, columns)` を実装（count/mean/std/min/max/median）。
    - 標準ライブラリのみでの実装を意図（pandas 等に依存しない）。

### Changed
- （初版のため履歴変更はなし）

### Fixed
- （初版のため修正履歴はなし）
  - ただしモジュール設計では以下のフェイルセーフ実装を採用:
    - OpenAI API の失敗時はゼロスコアでフォールバックしプロセス継続。
    - DuckDB の executemany に対して空リストを渡さない防御（互換性考慮）。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数の扱いに配慮:
  - OS 環境変数を保護するため `.env` の上書き制御と保護セットの概念を導入。
  - API キー（OpenAI 等）は関数引数で注入可能にしてテスト容易性と直接参照を分離。

注記・設計判断
- ルックアヘッドバイアス防止:
  - AI スコアリング / レジーム判定 / ファクター計算は内部で datetime.today()/date.today() を直接参照せず、引数として渡される target_date に基づき計算する設計。
- DuckDB を主要な永続化基盤として想定。SQL と Python の組合せで計算・集約を行う。
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を想定。テスト容易性のため呼び出し部を差し替え可能（ユニットテスト用に patch 可能な設計）。
- 実運用リスク低減のため、API エラーはリトライ/フォールバックしてプロセスを継続する方針（部分処理失敗時は既存データを不必要に消さない書き込み戦略を採用）。

貢献者
- 初期実装: コードベースから推測して作成（自動生成された CHANGELOG のため個別のコントリビュータ表記は省略）。

--- 

（必要であれば、各モジュールごとの公開 API サマリや注意点（DuckDB スキーマ期待値、必要な環境変数一覧、OpenAI の利用制限など）を追記します。どのレベルで詳細化するかご指定ください。）