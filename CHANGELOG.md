# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

注: 日付はリポジトリ内の初期バージョン実装に基づき推定しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-01

初期リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点と設計方針は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化 (バージョン: 0.1.0)。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行い、カレントワーキングディレクトリに依存しない設計。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env と .env.local の読み込み優先度: OS 環境変数 > .env.local > .env。.env.local は override=True（ただし OS 環境変数で保護されたキーは上書き不可）。
  - .env パースの堅牢化:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを提供）
    - PID_FILE_PATH, CPU/MEMORY/DISK しきい値（デフォルト値あり）
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/...）
    - is_live/is_paper/is_dev ヘルパー

- AI モジュール（kabusys.ai）
  - ニュースセンチメント (news_nlp)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols から銘柄単位で記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出して ai_scores テーブルへ書込む。
    - バッチ処理: 最大 20 銘柄/コール、1銘柄あたり最新最大 10 記事、最大文字数トリム（3000 文字）。
    - 再試行・バックオフ: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ（設定: 最大リトライ3回、初回待機1秒）。
    - レスポンス検証: JSON の抽出・バリデーション（results 配列、code と score の存在、未知コードは無視、スコアを ±1.0 にクリップ）。
    - タイムウィンドウ: target_date に対して JST ベースで前日 15:00 ～ 当日 08:30（UTCに変換して DB 比較）。calc_news_window を提供。
    - フェイルセーフ: API 失敗時は処理をスキップまたは該当チャンクを空として継続し、例外を上位に伝播させない（ただし API キー未設定は ValueError）。
    - DuckDB への書込は冪等設計（DELETE → INSERT を executemany で実行、空リストバインド回避）。
  - 市場レジーム判定 (regime_detector)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書込む。
    - MA 計算: target_date 未満のデータのみ使用し、データ不足時は中立（1.0）にフォールバックして警告ログ出力。
    - マクロニュース抽出: 定義済みマクロキーワードで raw_news をフィルタ（最大 20 件）。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）。
    - 合成スコアは clip(-1..1)、閾値で regime_label を bull/neutral/bear に分類（閾値: 0.2）。
    - DB 書込はトランザクション制御（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。失敗時は ROLLBACK を試行し例外を伝播。

- データ基盤モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理と営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar テーブルが未登録の場合は曜日ベースでフォールバック（土日を非営業日扱い）。
    - next/prev_trading_day は最大探索上限（60 日）を設定し無限ループを防止。
    - calendar_update_job(conn, lookahead_days=90): J-Quants から差分取得し market_calendar を冪等更新。バックフィル（直近 7 日）と健全性チェック（将来日付の異常検出）を実装。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを実装（取得/保存件数、品質問題、エラー一覧などを保持）。to_dict メソッドでシリアライズ可能。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（詳細は pipeline モジュール内コメント参照）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - factor_research
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev（MA200乖離）を計算。200 行未満の場合は None。
    - calc_volatility(conn, target_date): 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。データ不足時は None。
    - calc_value(conn, target_date): raw_financials から最新財務を取得し PER（EPS が 0/NULL の場合は None）と ROE を計算。
    - 設計: DuckDB SQL を中心とした実装で外部 API へはアクセスしない、結果は date/code を含む dict のリストで返却。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターンを一括取得する汎用実装（horizons のバリデーションあり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装。3 件未満は None を返す。
    - rank(values): 同順位は平均ランクを与えるランク変換。丸め（round 12）で ties の誤差を抑制。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。

- 共通設計上の注意点（全体）
  - ルックアヘッドバイアス防止のため、各アルゴリズムは datetime.today() / date.today() を内部計算の基準に直接使用しない（target_date を明示的に引数として受ける）。
  - OpenAI 連携関連では API 失敗時のフェイルセーフ動作（中立スコアやスキップ）を採用し、処理全体のロバスト性を高める。
  - DuckDB をデータ層の主要 DB として使用。DB 書込時は冪等性とトランザクション制御を重視。
  - API キー未設定時は ValueError を投げて明確に失敗させる設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーなどの機密情報は Settings 経由で環境変数から取得する想定。自動 .env ロードはデフォルトで有効だが、テストや CI 環境向けに KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化を提供。

---

開発・運用で注意する点:
- OpenAI 呼び出しはコストとレイテンシーを伴うため、実運用では API 呼び出し頻度とバッチ戦略、リトライ設定を環境や予算に合わせて調整してください。
- DuckDB executemany に空リストを渡すとエラーとなるため、コード内で明示的に空チェックを行っています。DB 層や DuckDB のバージョン差異に注意してください。
- .env パースは多くのケースに対応していますが、特殊なフォーマットの .env を使用する場合は挙動を確認してください。

（必要であれば、今後のリリース予定や既知の拡張点（例: strategy / execution 実装、webフロントエンド、追加の品質チェックルールなど）を追記します。）