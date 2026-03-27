# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
初回リリースの内容は、ソースコードから推測してまとめたものです。

## [0.1.0] - 2026-03-27

初回リリース（アルファ相当）。以下の主要機能・モジュールを追加しました。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - パブリックサブパッケージ: data, strategy, execution, monitoring（__all__ エクスポート）

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動ロード（プロジェクトルートを .git または pyproject.toml で検出）
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 高度な .env パーサ実装
    - export プレフィックス対応、クォート・バックスラッシュエスケープ対応、インラインコメントの扱い
  - 環境変数取得ユーティリティ Settings を提供（settings オブジェクト）
    - 必須環境変数チェック（未設定時 ValueError を送出）
    - 主要キー（例）:
      - JQUANTS_REFRESH_TOKEN（J-Quants）
      - KABU_API_PASSWORD / KABU_API_BASE_URL（kabuステーション API）
      - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知）
      - DUCKDB_PATH / SQLITE_PATH（デフォルト path を持つ）
      - KABUSYS_ENV（development / paper_trading / live のバリデーション）
      - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
    - is_live / is_paper / is_dev の便宜プロパティ

- AI（ニュース NLP / レジーム判定） (src/kabusys/ai/)
  - ニュースNLP: score_news（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）のJSONモードでセンチメントスコアを取得
    - 特徴:
      - タイムウィンドウ定義（JST: 前日15:00〜当日08:30 → UTC に変換）
      - バッチ処理（最大20銘柄／APIコール）
      - 1銘柄あたり: 最大記事数（デフォルト10件）・最大文字数トリム（デフォルト3000字）
      - リトライ（429, ネットワーク断・タイムアウト・5xx）に対する指数バックオフ実装
      - レスポンスバリデーション（JSON抽出、results リスト、コード一致、数値チェック）
      - スコアを ±1.0 にクリップ
      - ai_scores テーブルへ冪等的に一部（取得成功分のみ）DELETE→INSERT
      - テスト容易性: _call_openai_api を patch して差し替え可能
      - OpenAI API キー: 引数 api_key または環境変数 OPENAI_API_KEY を参照（未設定時 ValueError）
  - 市場レジーム判定: score_regime（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離 (ma200_ratio) と、マクロニュース由来の LLM センチメントを重み合成（70% / 30%）して市場レジーム（bull/neutral/bear）を日次判定
    - 特徴:
      - prices_daily と raw_news からデータ抽出（ルックアヘッドバイアス防止のため target_date 未満のみ使用）
      - マクロニュースはキーワードフィルタ(_MACRO_KEYWORDS)で抽出、最大件数制限
      - OpenAI 呼び出しは JSON モードでパース、API失敗時は macro_sentiment=0.0 でフォールバック（例外を投げず継続）
      - 合成スコアはクリップされ、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
      - テスト容易性: _call_openai_api を patch 可能
      - OpenAI API キー要（api_key または OPENAI_API_KEY）

- データプラットフォーム関連 (src/kabusys/data/)
  - ETL パイプラインの公開インターフェース（ETLResult を再エクスポート）
  - pipeline モジュール（src/kabusys/data/pipeline.py）
    - ETLResult dataclass（target_date・取得/保存件数・quality_issues・errors 等）
    - DB テーブル存在チェック、最大日付取得などのユーティリティ
    - 市場カレンダー補助（_adjust_to_trading_day 等、内部関数の準備）
    - 設計: 差分取得、バックフィル処理、品質チェック（quality モジュール）を想定
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理ユーティリティ
    - 提供関数:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等的に更新
    - 設計上の挙動:
      - market_calendar がない場合は曜日ベース（平日＝営業日）でフォールバック
      - DB 登録あり → DB 値優先、未登録日は曜日フォールバックで一貫性を保つ
      - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル、健全性チェックあり
    - jquants_client との連携ポイントを想定

- リサーチ（因子計算・特徴探索） (src/kabusys/research/)
  - factor_research（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev の計算（prices_daily参照）
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio 等
    - calc_value: per / roe（raw_financials と prices_daily の結合）
    - 全関数は DuckDB 接続を受け取り、外部APIや実口座にはアクセスしない設計
    - データ不足時には None を使用
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）に対する将来リターンの計算（LEAD を活用）
    - calc_ic: スピアマン順位相関（Information Coefficient）の計算（rank を内部で使用）
    - rank: 同順位は平均ランクで処理（round(v,12) による安定化）
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ
  - research パッケージは kabusys.data.stats の zscore_normalize を re-export（src/kabusys/research/__init__.py）

### 変更（設計上・実装上の注記）
- OpenAI 連携
  - 使用モデル: gpt-4o-mini（デフォルト）
  - JSON Mode を利用して厳格な JSON 応答を期待するが、パーサは前後の余計なテキストを抽出して復元する耐性を持つ
  - 再試行（リトライ）・バックオフ・フェイルセーフ（LLM失敗時に例外を上位に伝播させず、置換/スキップする）を設計方針として採用
- DB 書き込み
  - 多くの書き込み操作は「冪等化」または一部置換（DELETE → INSERT）で実装されており、部分失敗時に既存データを守る設計
  - DuckDB を前提にした実装（executemany の空パラメータ回避など、バージョン差分への配慮あり）
- ルックアヘッドバイアス対策
  - 多くの関数は datetime.today()/date.today() を内部で参照しない設計（外部から target_date を注入して deterministic に実行可能）
- テスト利便性
  - OpenAI 呼び出しを行う内部関数はパッチ可能に設計（unittest.mock.patch による差し替えを想定）
- .env ロード
  - プロジェクトルート検出は __file__ を起点に親ディレクトリを上方向へ探索するため、CWD 依存性を低減

### 修正（バグ修正等）
- 初回リリースのため該当なし（実装はコードベースからの推測）

### セキュリティ
- 初期実装では外部 API キー（OpenAI 等）を環境変数または引数で取得するようにしており、秘密情報を直接ハードコードしない設計

---

注記:
- 本 CHANGELOG は提供されたソースコードをもとに機能・設計・動作を推測して作成しています。実際のリリースノートや変更履歴と差異がある可能性があります。追加のコミット履歴や開発ノートがあれば、より正確な CHANGELOG を作成できます。