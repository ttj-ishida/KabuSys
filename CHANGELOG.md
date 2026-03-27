# KEEP A CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
この CHANGELOG はコードベース（初期公開）から推測して作成したリリースノートです。

## [0.1.0] - 2026-03-27

初回リリース（ベータ相当）。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）とバージョン定義を追加 (0.1.0)。
  - モジュール公開インターフェースを整理（data, strategy, execution, monitoring を __all__ で公開）。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索して決定。
  - .env パーサを実装し、export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env。既存 OS 環境変数は protected として上書きを防止。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベルなどのプロパティを公開。必須環境変数未設定時は ValueError を送出。
  - KABUSYS_ENV・LOG_LEVEL の値検証（許容値の列挙）を実装。

- AI（ニュース NLP / レジーム判定）
  - ニュース NLP モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込む score_news を実装。
    - JST ベースのニュース時間ウィンドウ計算（前日 15:00 ～ 当日 08:30 JST）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数上限・文字トリム、レスポンスバリデーション、スコアクリップ（±1.0）を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライを実装。失敗時は該当チャンクをスキップし、全体処理継続のフェイルセーフ設計。
    - テスト容易性のため _call_openai_api の差し替え（patch）を想定した設計。
  - 市場レジーム判定モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ冪等的に書き込む score_regime を実装。
    - LLM 呼び出しは gpt-4o-mini、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - MA 計算・ニュース取得はルックアヘッドバイアスを避ける（target_date 未満・前日のウィンドウ指定）設計。

- データ関連 (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し market_calendar テーブルへ冪等保存。
    - 営業日判定ユーティリティ群を提供：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未取得時の曜日ベースフォールバック（主に土日除外）と、DB に断片的データがある場合の一貫した動作を確保。
    - 探索上限 (_MAX_SEARCH_DAYS)、先読み・バックフィル日数、健全性チェックを設定。
  - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py)
    - ETLResult データクラスを公開し、ETL の取得件数・保存件数・品質チェック結果・エラー一覧を集約。
    - 差分更新、バックフィル、品質チェックの方針を実装（設計に基づく）。
    - jquants_client と quality モジュールを利用するインターフェースを想定。

- 研究（Research）ツール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比）およびバリュー（PER, ROE）を計算する calc_momentum, calc_volatility, calc_value を追加。
    - DuckDB クエリを主体とし、prices_daily / raw_financials のみ参照する安全な設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC（Spearman の ρ）計算 calc_ic、ランク変換ユーティリティ rank。
    - ファクター統計サマリーを返す factor_summary。
  - 研究ユーティリティ群をパッケージで公開（zscore_normalize の参照エクスポート等含む）。

- ドキュメント的実装
  - 各モジュールに詳細な docstring を追加し、設計方針・処理フロー・フェイルセーフ挙動・テスト指針を明記。

### 変更 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- なし（初回リリース）。ただし下記の堅牢性対策を含む実装上の配慮を行っています：
  - DuckDB の executemany に空リストを与えないようガード。
  - OpenAI API レスポンスの JSON パース不備に対するフォールバック（最外の {} の抽出）や例外ハンドリング。
  - DB 書き込み時のトランザクション制御（BEGIN / DELETE / INSERT / COMMIT）と例外発生時の ROLLBACK 保護。

### 非推奨 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。未設定時には明示的に ValueError を送出し、キー漏洩のリスク低減に配慮。
- 環境変数の上書き制御（protected set）により OS 環境変数を誤って上書きすることを防止。

---

注記:
- OpenAI 呼び出しは gpt-4o-mini を前提に実装されており、JSON Mode を利用して厳密な JSON 出力を期待しています。実運用では API レスポンスの変動に備えた監視とレート制御の運用が推奨されます。
- ルックアヘッドバイアス防止のため、すべての「当日基準」計算は target_date を明示的に受け取り、datetime.today()/date.today() を参照しない設計になっています（ただし calendar_update_job 等は実行日を基準にするため date.today() を使用している箇所があります）。
- テスト容易性のため、OpenAI の呼び出し関数は patch 等で差し替え可能な設計例が含まれています（_call_openai_api の差し替え等）。

今後の予定（例）:
- strategy / execution / monitoring の具象実装（アルゴリズム・発注ロジック・監視アラート）を追加。
- テストカバレッジ拡充・CI パイプライン整備。
- 外部 API クライアント（jquants_client 等）の完全実装と運用検証。

----------
（この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴やリリースノートと差異がある可能性があります。）