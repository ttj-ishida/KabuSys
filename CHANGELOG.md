# Changelog

すべての重要な変更は Keep a Changelog の形式で記載します。  
このファイルは手元のコードベースから推測して生成した初期の変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点の作業中の変更点はありません。リリース済みは下記参照）

## [0.1.0] - 2026-04-02

初回公開リリース（推定）。以下の主要機能と設計上の要点を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージ（__version__ = 0.1.0）。
  - パッケージ公開インターフェースの定義（__all__）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local ファイルの自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）。
  - export 構文・クォート・インラインコメント等に対応した堅牢な .env パース実装。
  - OS 環境変数を保護する protected オプション（.env の上書きを制御）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ。
  - Settings クラスで各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）と既定値（KABU_API_BASE_URL など）を提供。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - パス設定（duckdb / sqlite / pid ファイル）と監視閾値（CPU/メモリ/ディスク）を環境変数から取得。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ計算（JST 前日15:00〜当日08:30、UTC 変換）を提供する calc_news_window。
  - チャンク（最大 20 銘柄）ごとのバッチ送信、1銘柄あたりの記事トリム（文字数・件数制限）。
  - API 呼び出しのリトライ（429・ネットワーク・タイムアウト・5xx を指数バックオフでリトライ）。
  - レスポンスの堅牢なバリデーション（JSON モードでも前後余計なテキストを許容して抽出、requested codes の検証、スコアの数値検査および ±1.0 クリップ）。
  - DuckDB の制約（executemany に空リスト不可）への対応を含む、部分成功時に他コードの既存スコアを保護する置換ロジック（DELETE→INSERT）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）200日移動平均乖離とマクロニュース（LLM）を組合せて日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - MA 計算（データ不足時は中立: 1.0）、マクロキーワードによるニュースフィルタ、OpenAI 呼び出し（gpt-4o-mini）での macro_sentiment 評価。
  - レジームスコア合成（重み付け: MA 70% / マクロ 30%、スコアクリップ）、しきい値に基づくラベル化。
  - API 失敗時のフェイルセーフ（macro_sentiment=0.0）、再試行ロジック、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - テスト容易性のため API キー注入と _call_openai_api の差し替えを想定。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などのモメンタム系ファクターを計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials からの EPS/ROE を利用した PER/ROE 計算（target_date 以前の最新財務データ参照）。
    - データ不足時に None を返す安全設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する SQL 実装。
    - calc_ic: スピアマン順位相関（IC）を計算する実装（リンク結合、欠損ハンドリング、最小件数チェック）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）・統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージから主要関数を再エクスポート。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先、未登録日は曜日ベースでのフォールバック、最大探索範囲の制限、バックフィルと健全性チェック。
    - calendar_update_job: J-Quants からの差分取得と冪等保存（fetch/save の呼び出しとログ）。
  - pipeline / ETL:
    - ETLResult データクラスによる ETL 実行結果の集約（取得数・保存数・quality_issues・errors 等）。
    - 差分更新、バックフィル、品質チェックを想定した ETL 設計の下地。
  - etl: pipeline.ETLResult の再エクスポート。

- テスト性・運用性
  - OpenAI 呼び出し関数はモジュール内で独自に実装しており、unittest.mock で差し替え可能。
  - 関数設計上ルックアヘッドバイアスを避けるため datetime.today()/date.today() の直接参照を極力排除（target_date を明示的に受け取る）。
  - DuckDB 周りの互換性考慮（空の executemany 回避、日付型変換ユーティリティ）。
  - ロギングを広く導入し、エラー時は例外の再送出とログ出力を明確に分離。

### Changed
- （初回リリースのため既存バージョンからの変更は無し。設計上の注記を含む）

### Fixed
- （コードに見られる堅牢性改善点を反映）
  - OpenAI の API エラー分類に基づくリトライ/フォールバック処理を実装（RateLimitError / APIConnectionError / APITimeoutError / APIError を考慮）。
  - DuckDB の executemany 空リスト制約に対する安全対策を導入。
  - market_calendar の NULL 値や未登録日の扱いについて明確なフォールバック（曜日ベース）と警告ログを実装。

### Security
- 環境変数読み込み時に OS 側の環境変数を保護する仕組み（protected set）を導入。.env による上書きを制御可能。
- API キーは明示的に引数で注入可能。未設定時は明示的に ValueError を発生させ、無意識のキー漏れを防止。

### Notes / Known limitations
- J-Quants クライアント（kabusys.data.jquants_client）や一部外部依存は本コードスナップショットで参照されるが、実装は別モジュールに依存。
- OpenAI モデルは gpt-4o-mini を想定し、JSON Mode（response_format={"type":"json_object"}）でのやり取りを前提としている。API の将来的な仕様変更に注意。
- レスポンスパース失敗や API の永続的障害時には、処理はフェイルセーフ的にスキップまたは中立値を採用する設計（完全停止させない）。
- DuckDB 特性やタイムゾーン扱い（UTC naive datetime）に起因する運用上の注意点があるため、本番運用時は時刻・型の整合性検証を推奨。

---

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要に応じて日付や項目の修正を行ってください。）