# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣習に従います。

次のバージョンが未リリースの場合は Unreleased に記載します。

## [Unreleased]
- 今後の変更をここに記載します。

## [0.1.0] - 2026-03-28
初回リリース（初期実装）。以下の主要機能・設計方針・挙動を導入しました。

### 追加 (Added)
- パッケージ基本
  - パッケージ名 kabusys を導入し、サブパッケージ（data, research, ai 等）を公開。
  - __version__ を "0.1.0" に設定。

- 環境設定 / config
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダを実装（プロジェクトルートを .git / pyproject.toml から探索するため CWD に依存しない）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env/.env.local の優先度管理を実装（.env.local は override=True、ただし既存の OS 環境変数は保護）。
  - .env パーサを実装:
    - 空行・コメント行（#）をスキップ。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - クォートなしのコメント扱いのルール（# の直前がスペース/タブのみコメントとみなす）を実装。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須環境変数取得（未設定時は ValueError を送出）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証（不正値で ValueError）。
    - duckdb/sqlite のデフォルトパス (data/kabusys.duckdb, data/monitoring.db) をサポート。
    - is_live/is_paper/is_dev の簡易判定プロパティを追加。

- AI モジュール
  - news_nlp: ニュース記事を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出し、ai_scores テーブルへ書き込む機能を実装。
    - 前日15:00 JST ～ 当日08:30 JST を対象とする時間ウィンドウ計算（calc_news_window）。
    - 記事は銘柄ごとに集計し、1銘柄あたりの記事数と文字数を上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。
    - 最大 _BATCH_SIZE（20）銘柄ずつバッチで API 呼び出し。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンスの厳密な JSON バリデーション（results 配列内の code/score 検証）、スコアは ±1.0 にクリップ。
    - 書き込みは部分失敗時に他コードの既存スコアを保護するため、対象 code のみ DELETE → INSERT の冪等操作。
    - テスト用に _call_openai_api を patch できる（モック容易性）。
  - regime_detector: 市場レジーム判定（'bull'/'neutral'/'bear'）を実装。
    - ETF 1321 の 200 日移動平均乖離（70% 重み）とマクロニュースの LLM センチメント（30% 重み）を合成。
    - マクロニュースはキーワードフィルタで抽出し、OpenAI により JSON 形式の macro_sentiment を取得。
    - API失敗時は macro_sentiment=0.0 のフェイルセーフを採用。
    - レジームスコアはクリップされ、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）で、テスト時の差し替えが可能。

- データ / data
  - calendar_management:
    - JPX カレンダー（market_calendar）管理と夜間バッチ更新（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が存在しない場合は曜日ベース（土日非営業日）でフォールバックする堅牢な設計。
    - DB に値があれば優先、未登録日は曜日ベースで補完する一貫性あるロジック。
    - カレンダー取得は jquants_client を使用し、保存も idempotent に行う想定（fetch/save を呼び出し）。
    - calendar_update_job はバックフィル・健全性チェック（将来の日付の異常検出）を行う。
  - pipeline / ETL:
    - ETLResult データクラスを実装し、ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を集約。
    - 差分更新・バックフィル・品質チェック（quality モジュール利用想定）を行うためのユーティリティ関数群を実装する基盤を導入。
    - _get_max_date 等の DB ヘルパーを提供。
    - jquants_client 経由で取得 → save_* により冪等保存する想定。

- Research / analytics
  - research パッケージ公開ユーティリティ（zscore_normalize の再エクスポート含む）。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS=0 等は None）。
    - 上記は DuckDB の SQL ウィンドウ関数を活用して効率的に実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を使用）を一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。3 レコード未満は None を返す。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
    - いずれも外部ライブラリに依存せず標準ライブラリ＋DuckDB で実装。

### 変更 (Changed)
- 初期リリースのため該当なし（新規実装）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- API キー（OpenAI 等）が未設定の場合は明示的に ValueError を発生させることで誤った動作を防止。
- .env ロード時に OS 環境変数を上書きしない既定動作と、重要キー保護（protected set）を実装。

### 設計上の注意点 / 既知の挙動
- ルックアヘッドバイアス対策: いずれのアルゴリズムも内部で datetime.today() / date.today() を参照しない設計（target_date を明示的に渡す）。
- OpenAI 呼び出し：JSON Mode を利用する想定。API レスポンスの不整合や失敗はフェイルセーフ（スコア 0.0 もしくは該当銘柄スキップ）で扱い、全体パイプラインを停止させない設計。
- テスト容易性: _call_openai_api 等の箇所は unittest.mock.patch による差し替えが想定されている。
- DuckDB 0.10 等の挙動（executemany の空リスト不可等）を回避するためのガードロジックを実装。

### 互換性（Breaking Changes）
- 初回リリースのため breaking change はありません。

---

注: 本 CHANGELOG は提供されたコードベースから推測して作成しています。実運用での API クライアント実装（jquants_client 等）や外部依存の挙動により実際の挙動が異なる場合があります。