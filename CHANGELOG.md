# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` として公開。
  - __all__ に主要サブパッケージ（data, research, ai, ...）を定義。

- 環境設定管理 (`kabusys.config`)
  - .env/.env.local 自動読み込み機能を実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に決定するため、カレントワーキングディレクトリに依存しない。
  - 読み込み順序: OS 環境変数 > .env.local > .env。`.env.local` は `.env` を上書き可能。
  - OS 側の環境変数を保護するため、読み込み時に protected キーセットを扱う実装。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能（テスト用）。
  - 行パースの堅牢化:
    - `export KEY=val` 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - クォート無しでの行内コメント解釈を細かく制御。
  - 必須設定取得ヘルパー `_require` と Settings クラスを提供:
    - J-Quants、kabuステーション、Slack、DB（DuckDB/SQLite）などの設定プロパティを定義。
    - `KABUSYS_ENV` と `LOG_LEVEL` の厳格なバリデーション（許容値は定義済み）。
    - `duckdb_path`/`sqlite_path` のデフォルト値と Path 型返却。

- AI モジュール (`kabusys.ai`)
  - ニュースセンチメント解析 (`news_nlp.score_news`)
    - raw_news と news_symbols を集約して銘柄単位で OpenAI（gpt-4o-mini）にバッチ送信し、ai_scores テーブルへ書き込み。
    - JST ベースのニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する `calc_news_window` を実装（UTC naive datetime を返す）。
    - 1 回の API コールで最大 20 銘柄（チャンク単位）処理、1 銘柄あたり最大記事数／文字数でトリム。
    - OpenAI API のリトライ（429・ネットワークエラー・タイムアウト・5xx）を指数バックオフで実装。
    - API レスポンスの強固なバリデーション: JSON の抽出・復元、results 配列形式、コード照合、数値変換、有限値確認、スコアの ±1 クリップ。
    - DuckDB に対する冪等的な書き込み（DELETE → INSERT、executemany を用いた個別 DELETE）を実装し、部分失敗時に既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（`_call_openai_api` を patch）。

  - 市場レジーム判定 (`ai.regime_detector.score_regime`)
    - ETF 1321（日経225連動型）の直近 200 日 MA 乖離（重み 70%）と、マクロニュース（LLM によるセンチメント、重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定。
    - MA 計算は target_date 未満データのみ使用してルックアヘッドを防止。
    - マクロ記事抽出はキーワードベースで最大 20 記事まで取得し、LLM により -1.0〜1.0 のマクロセンチメントを算出。
    - OpenAI 呼び出しのリトライ／フェイルセーフ（API失敗時は macro_sentiment=0.0 継続）。
    - レジームスコア合成ロジックと閾値定義、結果を market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等的に保存。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（`_call_openai_api` を patch する想定）。

- Research モジュール (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true range の平均）、ATR の相対値（atr_pct）、20日平均売買代金、出来高比率を計算。NULL・不足行数処理を考慮。
    - calc_value: raw_financials から最新財務データ（report_date <= target_date）を取り込み、PER（EPS が 0/欠損時は None）・ROE を計算。
    - DuckDB 上で SQL を駆使して高効率に計算し、(date, code) をキーとする辞書リストを返却。

  - 特徴量探索 (`research.feature_exploration`)
    - calc_forward_returns: target_date から指定ホライズン（日数）先の終値を LEAD で取得し将来リターンを計算。horizons のバリデーション（正の整数、<=252）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。有効レコードが3件未満なら None。
    - rank: 同順位は平均ランクを採るランク変換（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。

- Data モジュール (`kabusys.data`)
  - カレンダー管理 (`data.calendar_management`)
    - JPX マーケットカレンダーの夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - 営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値優先・未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 安全策: 最大探索日数、バックフィル、健全性チェック（将来日付の異常検知）を実装。
    - market_calendar が空の場合は土日ベースのフォールバックを使用。

  - ETL パイプライン (`data.pipeline`, `data.etl`)
    - ETLResult データクラスを公開して ETL 実行結果を集約（取得数、保存数、品質問題、エラー一覧 等）。
    - 差分更新・バックフィル・品質チェックの設計方針とユーティリティ関数（テーブル存在確認、最大日付取得など）を実装。
    - jquants_client と quality モジュールを想定した連携設計（柔軟な id_token 注入などテスト容易性配慮）。

- モジュールエクスポートの整理
  - 各サブパッケージで主要関数/ユーティリティを __all__ にて公開（例: kabusys.ai.__all__、kabusys.research.__all__、data.etl の ETLResult 再エクスポート等）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- （初期リリースのため該当なし）

### Notes / Migration
- AI 機能（score_news, score_regime）は OpenAI API キー（環境変数 OPENAI_API_KEY または api_key 引数）が必須。キーが未設定の場合は ValueError を送出する。
- DuckDB 上の想定テーブル（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime など）が存在することが前提。テーブルが存在しない場合は一部関数は空結果や例外になるので注意。
- テスト時の利便性のため、OpenAI 呼び出しはモジュール内 private 関数を patch して差し替え可能。自動 .env 読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- DB への書き込みは冪等性を意識した設計（DELETE→INSERT、トランザクション管理）になっているが、DuckDB のバージョン差異（executemany の空リストなど）に配慮した実装が行われている。

もしこの CHANGELOG に追加してほしい細かい注記（例えば各テーブルのカラム要件やサンプル設定ファイルの例、既知の制限事項など）があればお知らせください。