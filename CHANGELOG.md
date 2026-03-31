# Changelog

すべての重要な変更をこのファイルに記載します。フォーマットは Keep a Changelog に準拠しています。  

- リリース日付は YYYY-MM-DD 形式です。  
- このリポジトリの初期バージョンは 0.1.0 です。

## [0.1.0] - 2026-03-31

初回公開リリース。

### 追加 (Added)
- パッケージ骨格を追加
  - パッケージ名: kabusys
  - エントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）
  - 公開モジュール: data, strategy, execution, monitoring（将来の拡張用プレースホルダ）

- 設定 / 環境変数管理
  - src/kabusys/config.py を実装
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）
    - 読み込み順序: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能
    - .env パーサ実装（コメント、export プレフィックス、クォート、エスケープ対応）
    - 環境値保護（protected set）を用いた上書き制御
    - Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル等）
    - 環境値検証（KABUSYS_ENV の許容値, LOG_LEVEL の許容値等）
    - 必須環境変数未設定時に ValueError を送出する _require ユーティリティ

- AI（自然言語処理）コンポーネント
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_score）を算出
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と UTC 変換関数 calc_news_window を提供
    - バッチ処理（最大 20 銘柄/リクエスト）、記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - JSON Mode を利用したレスポンス検証と堅牢なパース（前後の余計なテキストから {} を抽出する復元処理含む）
    - レートリミット・ネットワーク・5xx に対する指数バックオフによるリトライ実装
    - レスポンス検証ロジック（results 配列・code の照合・スコア数値の検証・±1.0 でクリップ）
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT、executemany の空リスト回避）
    - テスト用フック: _call_openai_api を patch して差し替え可能
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム判定（bull / neutral / bear）を行う機能を実装
    - prices_daily から MA200 乖離計算（ルックアヘッドバイアス防止: target_date 未満のみ使用）
    - raw_news からマクロキーワードに一致する記事タイトルを収集し OpenAI で macro_sentiment を評価
    - API 失敗やパース失敗は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - レジームスコア合成と market_regime テーブルへの冪等的書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - OpenAI 呼び出しは個別実装でモジュール結合を避ける設計（テスト容易性のため差し替え可能）

- Research（因子計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を計算する関数群を実装
    - DuckDB SQL を用いた効率的な窓関数実装（LAG/AVG/ROW_NUMBER 等）
    - データ不足時は None を返す（安全な欠損扱い）
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証あり）
    - IC（Information Coefficient）計算（スピアマンのランク相関を実装）
    - ランク変換（同順位は平均ランク、浮動小数丸め対策あり）
    - ファクター統計サマリー（count/mean/std/min/max/median）
  - research パッケージの __all__ を整備してユーティリティを公開

- Data（データ管理・ETL）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブルとの連携、夜間バッチ更新用 calendar_update_job）
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB データがない場合の曜日ベースのフォールバック（週末を非営業日とする）
    - 最大探索日数制限と健全性チェック（最大探索日や未来日付チェック）
    - J-Quants クライアントとの連携を想定（jquants_client.fetch_market_calendar 等）
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラーメッセージ等）
    - 差分更新・バックフィル・品質チェックを行うための内部ユーティリティ（_get_max_date など）
    - DataPlatform の設計方針に沿った差分取得・保存・品質チェックの枠組みを提供
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート（公開インターフェース）

- その他ユーティリティ
  - DuckDB を主要なデータストアとして想定した実装（型変換ユーティリティ、テーブル存在チェック等）
  - ロギングを各モジュールに配置し詳細な実行ログ出力をサポート
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。環境変数や API キーの扱いには注意（Settings._require による必須チェックや自動ロード保護を実装）。

### 注意事項 / 使用上のメモ
- OpenAI API を使用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。関数呼び出し時に api_key を渡すか、環境変数を設定してください。
- .env 自動読み込みはプロジェクトルートの検出に依存します。配布後やテスト時に自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany は空リストを受け付けないバージョンの振る舞いを考慮した実装になっています（params が空のときは操作をスキップ）。
- LLM 呼び出しはネットワーク障害や 5xx, 429 に対してリトライやフォールバック（ゼロスコア）を実装していますが、API 利用料やレート制限には注意してください。
- 多くの関数はルックアヘッドバイアスを避けるため target_date を明示的に受け取り、DB クエリは target_date 未満 / 排他区間等で実装されています。

### 互換性に関する注記 (Breaking Changes)
- 初回リリースのため該当なし。

----- 

今後は、バグ修正、機能拡張（発注/実行ロジック・モニタリング統合・UI など）、テストカバレッジ強化、ドキュメント追加を予定しています。