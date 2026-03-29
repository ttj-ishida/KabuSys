# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース: kabusys 基本モジュール群を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に `__version__ = "0.1.0"` と `__all__` を定義。

- 環境設定 / ローダー:
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。自動読み込みは OS 環境変数 > .env.local > .env の順で優先される。
    - プロジェクトルート検出機能を追加（.git または pyproject.toml を起点に探索）。パッケージ配布後も CWD に依存せず動作。
    - .env パーサ実装: export 形式、クォート（シングル/ダブル）のエスケープ処理、インラインコメントの取り扱いをサポート。
    - 読み込み失敗時の警告出力、読み込み上書き制御（override、protected）を提供。
    - Settings クラスを提供し、主要設定（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）をプロパティで取得可能。未設定の必須環境変数は ValueError を送出。
    - 環境種別・ログレベルの妥当性チェック（許容値の列挙）を導入。

- AI（ニュース NLP / レジーム判定）:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。
    - 集約ウィンドウ: JST の前日 15:00 〜 当日 08:30（内部は UTC naive datetime に変換）。
    - チャンクバッチ処理（最大 20 銘柄 / コール）、記事数・文字数上限（記事数最大 10 件、文字数 3000）でトークン肥大を抑制。
    - JSON Mode を利用し、レスポンスのバリデーションとスコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他エラーはスキップして継続するフェイルセーフ設計。
    - DuckDB への書き込みは冪等（対象コードのみ DELETE → INSERT）。DuckDB の executemany の空リスト制約に対応。
    - テスト容易性: OpenAI 呼び出し箇所を patch できるように内部関数で分離。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）について 200 日移動平均乖離（重み 70%）と、ニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存する処理を実装。
    - マクロキーワードフィルタ、OpenAI（gpt-4o-mini）呼び出し、再試行ロジック、API 失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - DuckDB からのデータ取得は target_date 未満のみを参照してルックアヘッドバイアスを防止。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）および失敗時の ROLLBACK 処理。

- データプラットフォーム / ETL / カレンダー:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーの管理機能を実装（market_calendar テーブルに基づく営業日判定、next/prev/get_trading_days、SQ 判定など）。
    - market_calendar が未取得の場合は曜日ベース（土日休み）でフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants からの差分取得、バックフィル（直近 n 日を再取得）、健全性チェック（極端な将来日を検出してスキップ）を実装。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの高レベル設計に対応するユーティリティを実装。
    - ETLResult データクラスを定義（取得件数、保存件数、品質チェック結果、エラーリストを保持）。品質問題は収集して呼び出し元で判断する設計（Fail-Fast ではない）。
    - 差分更新、backfill、品質チェックとの連携を想定した実装（jquants_client / quality モジュール経由で保存・検査）。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポートインターフェースを追加。

- 研究（Research）ユーティリティ:
  - src/kabusys/research/factor_research.py
    - ファクター計算（Momentum / Volatility / Value / Liquidity の一部）を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を算出（必要データ不足時は None）。
    - Value: raw_financials を用いた PER / ROE 計算（EPS が 0 または欠損なら PER は None）。
    - すべて DuckDB SQL を用いた実装で、ルックアヘッドバイアスに注意。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン（任意ホライズン）の一括取得クエリを実装（デフォルト horizons=[1,5,21]）。
    - IC（Spearman の ρ）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）など統計解析ユーティリティを実装。
    - 標準ライブラリのみで実装し、外部依存を避ける設計。

- データ／AI テスト支援:
  - OpenAI 呼び出し部分を内部関数として切り出しており、unittest.mock.patch による差し替えでテスト可能。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- （初期リリースのため該当なし）

---

注意事項（使用上のポイント）
- OpenAI API キーは関数引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出する設計。
- LLM 呼び出しの失敗は基本的にフォールバック（0.0 スコアやスキップ）して処理を継続するため、外部 API 障害時でもシステム全体が停止しにくい作りになっています。ただし、API キー未設定などは例外になるため注意してください。
- 時刻の扱い: ニュース集約ウィンドウはドキュメントに従い JST ベースで設計され、内部では UTC naive datetime を使用して DB クエリと比較しています（ルックアヘッド回避）。
- DuckDB への書き込みは冪等性を考慮しており、部分失敗時に既存データを不必要に消さないよう配慮しています。

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノート作成時はコミット履歴や変更差分を参照してください。）