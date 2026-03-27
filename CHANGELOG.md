# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

※ 本ドキュメントはコードベースから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-27
最初の公開リリース。

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ エクスポート: data, strategy, execution, monitoring

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数の自動読み込み機能を実装
    - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
  - .env 行のパース機能を強化（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）
  - .env ファイル読み込み時の保護キー（既存 OS 環境変数の保護）対応と override オプション
  - 必須環境変数未設定時にわかりやすいエラーメッセージを出す _require 関数
  - Settings クラスで主要設定をプロパティとして提供
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須
    - KABU_API_BASE_URL, DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）などのデフォルト値
    - KABUSYS_ENV に対する検証（development / paper_trading / live）
    - LOG_LEVEL に対する検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
    - score_news(conn, target_date, api_key=None)
      - 前日15:00 JST〜当日08:30 JST のニュースを対象とするタイムウィンドウ計算（calc_news_window）
      - raw_news / news_symbols から銘柄ごとに記事を集約（1銘柄あたり最大記事数・文字数でトリム）
      - OpenAI（gpt-4o-mini）へバッチ送信（1回最大20銘柄）
      - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ
      - JSON モードレスポンスのバリデーション（results 配列、code/score 検証）、スコアは ±1.0 にクリップ
      - 成功した銘柄のみ ai_scores テーブルへ冪等的に書き換え（DELETE → INSERT）
    - 内部: _fetch_articles, _score_chunk, _validate_and_extract, _call_openai_api 等
    - テスト容易性: OpenAI 呼び出しは個別関数に切り出し、ユニットテストで差し替え可能
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定
      - ma200_ratio 計算（_calc_ma200_ratio: ルックアヘッド防止のため target_date 未満のデータのみ使用）
      - マクロキーワードで raw_news タイトルを抽出（最大 20 件）
      - OpenAI（gpt-4o-mini）でマクロセンチメント評価（JSON パース・リトライ・フォールバック）
      - 合成スコアの閾値判定（BULL_THRESHOLD / BEAR_THRESHOLD）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - マクロキーワードのセット、モデル名、リトライ回数、重み付け等の定数を定義

- データモジュール (`kabusys.data`)
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの夜間バッチ更新ジョブ (calendar_update_job)
      - J-Quants クライアント経由でカレンダーを差分取得 → market_calendar テーブルへ冪等保存
      - バックフィル、先読み、健全性チェック（将来日付の異常検出）を実装
    - 営業日判定および探索ユーティリティ
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - market_calendar のデータが不十分な場合は曜日ベースのフォールバック（週末を非営業日扱い）
      - 最大探索範囲で無限ループ回避
  - ETL パイプライン (`kabusys.data.pipeline`)
    - ETLResult データクラス（ETL 実行結果、品質問題・エラー管理、シリアライズ to_dict）
    - 差分更新・バックフィル・品質チェック方針を反映したユーティリティ
    - 内部ユーティリティ: テーブル存在確認、最大日付取得、トレーディングデイ調整など
  - etl.py で ETLResult を再エクスポート

- リサーチモジュール (`kabusys.research`)
  - factor_research
    - calc_momentum(conn, target_date)
      - 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算
      - データ不足時は None を返す挙動
    - calc_volatility(conn, target_date)
      - 20 日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算
      - true_range の NULL 伝播を制御して正確に ATR を計算
    - calc_value(conn, target_date)
      - raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0 または NULL の場合は None）
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None)
      - 指定ホライズン先の将来リターン計算（デフォルト [1,5,21]）
      - horizons のバリデーション（1〜252 の整数）
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンランク相関（IC）を計算。有効レコード < 3 の場合は None を返す
    - rank(values)
      - 同順位は平均ランクを割当てるランク化ユーティリティ（丸めて ties 検出）
    - factor_summary(records, columns)
      - 各カラムの count/mean/std/min/max/median を計算

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security
- OpenAI API キーや各種トークンは環境変数経由で管理することを想定
  - OpenAI 呼び出しを伴う関数（score_news, score_regime）は api_key 引数で注入可能（テスト／運用分離を容易にする）
- .env 読み込みで既存 OS 環境変数はデフォルトで保護される（上書き防止）

### Notes / Implementation details
- DuckDB を主要なローカル分析 DB として利用（duckdb パッケージに依存）
- OpenAI の Chat Completions API を gpt-4o-mini モデルで使用（response_format={"type": "json_object"} を想定）
- LLM 連携処理は堅牢性を重視
  - 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ
  - パース失敗・致命的 API エラー時は例外を投げずフォールバック（0.0 やスキップ）する設計が多い
- ルックアヘッドバイアス対策として、日付参照は date.today()/datetime.today() を直接利用しない実装方針を採用（関数引数として target_date を受ける）
- DuckDB の executemany に関する互換性考慮（空リスト渡し回避）など、実行環境依存の注意点に対応

---

過去のリリースについてはここに追記していきます。今後のリリースでは機能追加、インターフェース変更、バグ修正等をカテゴリに分けて記載します。