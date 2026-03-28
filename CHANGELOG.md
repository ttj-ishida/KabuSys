# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
重要な変更点（機能追加・修正・仕様）を日本語でまとめています。

全般
- 初版リリース (v0.1.0)。パッケージの基本構成・データ処理・研究用ユーティリティ・AI ベースのニュース解析・市場レジーム判定などのコア機能を実装。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ全体
  - kabusys パッケージ初期化とバージョン定義を追加（__version__ = "0.1.0"）。
  - 公開 API の __all__ を定義（data, strategy, execution, monitoring）。

- 設定 / 環境読み込み (src/kabusys/config.py)
  - .env / .env.local からの自動環境変数読み込みを実装（プロジェクトルートは .git / pyproject.toml から探索）。
  - .env のパース実装（コメント、export プレフィックス、クォート／エスケープ対応、インラインコメントの扱い）。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、アプリケーション設定（J-Quants / kabuステーション / Slack / DB パス / 環境 / ログレベル等）をプロパティで取得可能に。
  - 必須環境変数未設定時は ValueError を投げる `_require` を実装。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI モジュール (src/kabusys/ai/)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出・ai_scores テーブルへ書き込む機能を実装。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）、最大記事数・文字数トリム、バッチング（最大 20 銘柄／回）などを実装。
    - JSON mode を用いたレスポンスのバリデーションとスコアの ±1.0 クリップ。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで行うフェイルセーフ実装。
    - テスト容易性のため、_call_openai_api の差し替え（patch）を想定。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出・market_regime テーブルへ冪等書き込み。
    - MA 計算はルックアヘッドバイアスを防ぐため target_date 未満のデータのみ使用。
    - マクロニュース抽出（タイトルにマクロキーワード一致） → OpenAI で JSON 出力（{"macro_sentiment": 0.0}）を取得 → リトライ & エラー時は macro_sentiment = 0.0 とするフェイルセーフ。
    - OpenAI 呼び出しは独立実装とし、テストで差し替え可能に。

- データプラットフォーム (src/kabusys/data/)
  - calendar_management モジュール
    - market_calendar を扱う営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーデータがない場合は曜日ベースでフォールバックする堅牢設計。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得→冪等保存（バックフィル・健全性チェック付き）を行う。
  - pipeline / etl
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー等を集約）。
    - ETL パイプラインの補助ユーティリティを実装（最終取得日の取得、テーブル存在チェック、差分取得の方針、バックフィル挙動など）。
    - etl モジュールで pipeline.ETLResult を再エクスポート。
  - jquants_client と quality モジュール（参照箇所あり）を想定した設計（実データ取得 / 保存 / 品質チェックを統合する ETL フロー）。

- 研究用ユーティリティ (src/kabusys/research/)
  - factor_research モジュール
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR/流動性/出来高関連、PER/ROE（raw_financialsより）といったファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL を用いて効率的に計算（ルックバック範囲やデータ不足時の None 処理を含む）。
  - feature_exploration モジュール
    - 将来リターン計算 calc_forward_returns（任意ホライズン）、IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）、rank ユーティリティ、各ファクターの統計サマリー factor_summary を追加。
    - 外部ライブラリに頼らず標準ライブラリのみで実装。

- テスト性 / 安全設計
  - OpenAI 呼び出しポイントをモジュール内で分離し、テスト時にモック可能に。
  - API エラー時のフェイルセーフ挙動（0.0 フォールバック、部分書き込み回避、ROLLBACK の試行と警告ログ）を各所に実装。
  - DuckDB executemany の制約（空リスト不可）を考慮した安全な DB 書き込み実装。

### 変更 (Changed)
- （初版のため過去バージョンからの変更はなし）

### 修正 (Fixed)
- （初版のため既存バグ修正はなし）

### 注意事項 / マイグレーションノート
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等が Settings で _require により必須として扱われるプロパティがあるため、実行前に .env を整備する必要があります。
- 自動 .env ロード:
  - パッケージ import 時にプロジェクトルートを探索して .env / .env.local を自動ロードします。CI／テスト環境や特定条件では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
  - .env.local は .env を上書き（override=True）しますが、OS の環境変数は保護されます。
- OpenAI API キー:
  - news_nlp.score_news と regime_detector.score_regime は api_key 引数を受け付けます。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError が発生します。
- DuckDB テーブル前提:
  - 各機能は特定の DuckDB テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）が存在する前提で動作します。テーブルが存在しない場合やデータ不足時の挙動（None / 0 / ログ出力）を仕様として取り入れています。

### セキュリティ (Security)
- 外部 API キーは環境変数で管理する設計。ログに API キーなどの機密情報を出力しないよう注意。

---

今後の案 (例)
- 0.2.x での予定（例）:
  - strategy / execution の実装拡張（バックテスト / 実注文ラッパー）
  - データ品質チェックの強化と詳細レポート
  - AI 評価の再現性向上（プロンプト管理・温度調整のオプション化）

変更・追加点の補足や改訂履歴の詳細が必要であれば、どのモジュールについて深掘りするかを教えてください。