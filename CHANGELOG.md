Changelog
=========
すべての重要な変更をここに記録します。これは Keep a Changelog の形式に準拠しています。  
フォーマット: [version] - YYYY-MM-DD、セクションは Added / Changed / Fixed / Deprecated / Removed / Security。

[Unreleased]
-----------

[0.1.0] - 2026-03-27
--------------------
Added
- 初回リリース。パッケージ kabusys 全体を公開。
- 基本情報
  - パッケージバージョンを `0.1.0` として定義（src/kabusys/__init__.py）。
  - エクスポート: data, strategy, execution, monitoring モジュールを公開。

- 環境設定: kabusys.config
  - .env/.env.local の自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パースは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント（スペース直前の#の扱い）に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 環境 (development/paper_trading/live) / ログレベル を環境変数から取得（必須キーは未設定時に ValueError を送出）。
  - デフォルトの DB パス（DuckDB / SQLite）の扱いや env/log_level の検証機能を実装。

- AI 機能: kabusys.ai
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄毎にニュースを結合し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ保存。
    - 時間ウィンドウは JST 基準で前日 15:00 ～ 当日 08:30（UTC に変換して DB 比較）。
    - バッチ処理（1回で最大 20 銘柄）、1銘柄あたり記事数・文字数の上限（デフォルト: 10 件 / 3000 文字）でトークン肥大化を抑制。
    - レート制限・ネットワーク断・タイムアウト・5xx 系は指数バックオフでリトライ。API エラーやレスポンスパース失敗はフェイルセーフでスキップ（例外を上げずにログ）。
    - レスポンスのバリデーション機構を実装（JSON 抽出、"results" リスト検証、既知コードのみ受け入れ、スコアを ±1.0 にクリップ）。
    - 書き込みは部分失敗時の既存データ保護のため、スコア取得済みコードだけを DELETE → INSERT（トランザクション）で置換。
    - テスト用に OpenAI 呼び出し部分（_call_openai_api）を patch して差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに冪等書き込み。
    - ma200_ratio は target_date 未満の価格データのみ使用してルックアヘッドを防止。データ不足時は中立（1.0）を採用。
    - マクロニュースはニュース N 件（最大 20 件）を取得し、OpenAI に渡して -1.0〜1.0 の macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 で継続。
    - レジームスコアは clip と閾値によってラベル付け（デフォルト閾値: bull ≥ 0.2、bear ≤ -0.2）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データプラットフォーム: kabusys.data
  - ETL/パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入（ETL 結果の集約: 取得件数、保存件数、品質問題、エラー等）。
    - 差分取得、バックフィルや品質チェックに関する設計方針を実装（バックフィルデフォルト 3 日、最小データ日付、カレンダー先読みなど）。
    - DuckDB を用いた最大日付取得ユーティリティ等を実装。
    - etl モジュールで ETLResult を再エクスポート。

  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar テーブル）の夜間更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得・冪等保存）。
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。market_calendar がない場合は土日を非営業日とするフォールバックを採用。
    - DB 登録値優先、未登録日は曜日ベースフォールバックで扱う一貫した挙動。検索上限（最大探索日数）や健全性チェックを導入。

- リサーチ機能: kabusys.research
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB 上で計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の挙動（NULL/None の扱い）を明確にし、結果は (date, code) をキーとした辞書リストで返す。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 指定 horizon の将来リターンを一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装し、データ不足時は None を返す。
    - ランク関数（rank）: 同順位は平均ランクを採用（丸めで ties 検出）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
    - これらは外部ライブラリに依存せず標準ライブラリと DuckDB を利用。

- 共通実装
  - DuckDB を前提とした SQL + Python ベースの処理（各モジュールで DuckDBPyConnection を引数に取る）。
  - OpenAI クライアント呼び出しは gpt-4o-mini をデフォルトで使用し、JSON Mode を利用して厳密な JSON 出力を期待する設計。
  - ロギングを広範に配置し、失敗は基本的にログに記録してフェイルセーフで継続する方針（特に外部 API 呼び出し周り）。
  - テスト容易性のため、内部の API 呼び出し関数は patch 可能に設計（例: _call_openai_api）。

Changed
-（初回リリースのため該当なし）

Fixed
-（初回リリースのため該当なし）

Deprecated
-（初回リリースのため該当なし）

Removed
-（初回リリースのため該当なし）

Security
-（初回リリースのため該当なし）

Notes / Implementation decisions
- ルックアヘッドバイアス防止: 全てのバッチ処理・スコアリング関数は datetime.today() / date.today() を内部で参照せず、明示的に target_date を引数に取る設計。
- 部分書き込み保護: AI スコア更新時はスコアを取得した銘柄のみを上書きすることで、部分失敗で既存データを毀損しない。
- DuckDB の executemany の制約（空リスト不可）に配慮した実装。
- OpenAI と外部 API のエラーは多くの場合「ログ & フォールバック」し、ETL/解析処理全体が中断しないように設計。

今後の TODO（推測）
- strategy / execution / monitoring モジュールの具体実装（公開済みトップレベルだが本リリースでは詳細が見当たらないため、別リリースで実装予定）。
- テストカバレッジの充実（OpenAI モックや DuckDB のテスト用フィクスチャ）。
- ドキュメント（API 使用例、DB スキーマ、運用手順）の拡充。

-----

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時はリポジトリのコミット履歴・リリース用チケット等を参照のうえ調整してください。