# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このプロジェクトの初期リリース履歴をコードベースから推測してまとめています。

全般なルール:
- すべてのリリースはセマンティックバージョニングに従います。
- 日付はリリース日（推定）を記載しています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - モジュール群を公開: data, strategy, execution, monitoring。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読込する仕組みを実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パース機能の実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント処理などに対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV/LOG_LEVEL）などのプロパティを環境変数から取得・検証。
  - 環境変数未設定時の明示的エラー（_require）や値検証（有効な env 値・ログレベルの検証）を実装。

- ニュース NLP（AI） (src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py)
  - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）を用いてセンチメントスコアを算出して ai_scores テーブルへ書き込むパイプラインを実装。
  - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST の記事）を提供（calc_news_window）。
  - バッチ処理（最大 20 銘柄／チャンク）、トークン増大対策（記事数・文字数上限）、JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ処理を実装。
  - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ。非リトライ系はスキップしてフェイルセーフに継続。
  - レスポンスの堅牢なパース（JSON 以外の余計な前後テキストが混在する場合の復元）と未知コードの無視、数値検証を実装。
  - テーブル書き込みは冪等に（DELETE → INSERT）実行し、部分失敗時に既存データを保護。

- マーケットレジーム判定（AI + テクニカル合成） (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定する score_regime を実装。
  - prices_daily/raw_news を参照して MA 計算・記事抽出を行い、OpenAI（gpt-4o-mini）で macro_sentiment を取得。API 失敗時はフェイルセーフで 0.0 を採用。
  - レジーム計算の閾値、スコア合成式、冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - OpenAI 呼び出しはモジュール内独立実装とし、テスト容易性のため差し替えポイントを確保。

- データ関連ユーティリティ (src/kabusys/data/*
  - calendar_management.py
    - JPX マーケットカレンダーの管理・夜間バッチ更新（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し冪等保存。
    - 営業日判定ロジック群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、探索範囲上限（_MAX_SEARCH_DAYS）や健全性チェックを実装。
  - pipeline.py / etl.py
    - ETLResult データクラスを公開（ETL 結果の集約、品質チェック結果/エラーリストを含む）。
    - ETL ユーティリティおよび差分取得・保存・品質チェックの設計方針を反映した基盤関数（内部ユーティリティ・テーブル存在チェック・最大日付取得など）を実装。
    - jquants_client と quality モジュールとの連携を想定した設計。

- リサーチ（研究）モジュール (src/kabusys/research/*)
  - factor_research.py
    - Momentum / Volatility / Value / Liquidity を含む定量ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を算出（データ不足時は None を返す）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。
      - calc_value: raw_financials と prices_daily を組み合わせ PER/ROE を算出。
    - DuckDB 上で SQL とウィンドウ関数を活用した実装で、外部 API に依存しない設計。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。入力検証（horizons 範囲）と効率的な一括クエリを実装。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算し、データ不足時は None を返す。
    - rank: 同順位は平均ランク扱いのランキング実装（丸めで ties のハンドリング）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。

- 内部設計方針の明示
  - ルックアヘッドバイアス防止のため、各種処理で datetime.today()/date.today() を直接参照しない設計を明示。
  - API 呼び出し失敗時は例外をそのまま投げず、適切にフォールバックするフェイルセーフ設計を採用（AI スコア処理など）。
  - DuckDB のバージョン差分に配慮した実装（executemany の空リスト回避、ANY(?)バインドの互換性回避など）。

### 変更 (Changed)
- 初期リリースのため該当なし（新規実装の集合）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 削除 (Removed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- 初期リリースのため該当なし。

---

注記:
- OpenAI クライアント周りは外部サービスに依存するため、API キーの注入（引数 or 環境変数 OPENAI_API_KEY）を各関数でサポートしています。テスト時に _call_openai_api をモックできるよう差し替えポイントを設けています。
- データ保存や更新は基本的に冪等設計（DELETE→INSERT、ON CONFLICT を想定）で安全化しています。
- 上記は現行ソースコードから推測した初期リリース内容です。実際のリリースノート作成時はコミット履歴・PR コメント等の補足情報を反映してください。