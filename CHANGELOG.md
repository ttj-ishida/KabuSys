# Changelog

すべての重要な変更はこのファイルに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。  

- リリース日はリポジトリ内のコードから推測して付与しています。
- 「推測」と明記した部分は、コード上の設計意図やコメントから推定した説明です。

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。
主な機能群は設定管理、データ ETL / カレンダー管理、研究用ファクター計算、AI ベースのニュース NLP／市場レジーム判定などです。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報とバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開インターフェースを __all__ で定義（data, research, ai, ... の想定公開モジュール）。
- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルートは .git / pyproject.toml から探索）。
  - .env パースの実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得ヘルパー _require と Settings クラスを実装。J-Quants / kabuステーション / Slack / DB / 監視用の主要設定プロパティを提供。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。
  - デフォルト値の設定（KABUSYS の DB パス・PID ファイルパス・閾値など）。
- データモジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得 → 冪等保存）。
    - 営業日判定ユーティリティ群を提供: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、安全性チェック、バックフィルロジックを実装。
  - ETL パイプライン (pipeline / etl)
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題リスト・エラー情報を保持）。
    - 差分取得・バックフィル・品質チェックを行う ETL の設計に対応するインターフェースを追加（実装の一部を含む）。
  - jquants_client / quality など外部モジュールへの依存を想定した設計（関数呼び出しで注入利用を想定）。
- AI モジュール (kabusys.ai)
  - ニュース NLP (news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
    - バッチ処理、1チャンク当たりの最大銘柄数、記事数・文字数トリム、JSON Mode 応答のバリデーションを実装。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフリトライを導入。API レスポンス検証により不正レスポンスはスキップし、フェイルセーフで継続。
    - score_news(conn, target_date, api_key=None) を公開 API として実装（返り値: 書き込んだ銘柄数）。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（ma200_ratio）と、マクロ経済ニュースの LLM センチメントを組み合わせて日次で市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ冪等的に保存する score_regime を実装。
    - マクロニュースはニュース NLP 用の時間ウィンドウで抽出、OpenAI で JSON レスポンス（{"macro_sentiment": x}）を期待。API失敗時は macro_sentiment=0.0 にフォールバック。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の順で冪等性を確保。
- 研究（Research）モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB SQL で計算して返却。
    - calc_volatility: 20 日 ATR（atr_20）や相対 ATR（atr_pct）、平均売買代金、出来高比などを計算して返却。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算して返却。
    - 設計上、prices_daily / raw_financials のみ参照しルックアヘッドバイアスを防止。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一度に算出。
    - calc_ic: スピアマンランク相関（IC）を実装（ランク付けは平均ランクの方法）。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで処理（丸め対策あり）。
  - 研究ユーティリティとして zscore_normalize を再エクスポート（kabusys.data.stats から）。
- テスト容易性
  - OpenAI 呼び出し関数は _call_openai_api のように内部で分離し、テスト中は unittest.mock.patch で差し替え可能に設計。

### 変更 (Changed)
- （初回リリースのため主要な「変更」項目はありません。上位設計や命名はドキュメントコメントに基づく設計思想を反映しています。）
- 各所で「ルックアヘッドバイアス回避」の設計方針を明確化（date.today() の未使用、DB クエリの排他条件適用など）。

### 修正 (Fixed)
- 各モジュールで不安定な外部 API や不正レスポンスに対してフェイルセーフ（0.0 やスキップ）を実装し、単一障害で全処理が止まらないようにしています（推定: 運用上の堅牢性向上）。
- DuckDB の executemany に空リストが渡るとエラーとなる問題に対処するガードを追加（空時は実行をスキップ）。

### 破壊的変更 (Removed / Deprecated)
- なし（初回リリース）。

### セキュリティ (Security)
- 環境変数の取り扱いを行う際に保護対象キー（OS 環境変数）を考慮した上書きロジックを用意しています（.env ロード時の protected セット）。  
- API キーは明示的に引数で注入可能にし、環境変数からの自動取得でもエラー時に明確な例外を投げることで鍵の未設定を速やかに検知できます。

---

注意:
- この CHANGELOG は提供されたソースコードとそのコメントから推測して作成しています。実際のリリースノートはリポジトリのコミット履歴やリリース管理情報を基に調整してください。