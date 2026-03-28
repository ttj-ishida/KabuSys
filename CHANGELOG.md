# CHANGELOG

すべての注目すべき変更履歴をここに記載します。本ファイルは Keep a Changelog に準拠します。  
バージョン番号は semantic versioning を想定しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコア機能を実装しました。主な追加点は以下の通りです。

### Added
- 全体
  - パッケージ初期版を公開（kabusys v0.1.0）。
  - パッケージトップでのエクスポート管理（__all__）を定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先度: OS環境変数 > .env.local > .env。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサを実装（export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理対応）。
  - Settings クラスを提供し、必須値チェック（_require）、デフォルト値、検証（KABUSYS_ENV / LOG_LEVEL の許容値）を行うプロパティを実装。
  - データベースパス（DuckDB / SQLite）や Slack / kabuステーション / J-Quants トークン等の設定を取り扱うプロパティを実装。

- データプラットフォーム (kabusys.data)
  - カレンダー管理モジュール (calendar_management)
    - market_calendar テーブルを参照した営業日判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない/未登録の場合は曜日ベース（週末除外）のフォールバック処理を行い一貫性を担保。
    - カレンダー夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants から差分取得 → 保存、バックフィル・健全性チェック付き）。
    - 最大探索日数やバックフィル・先読み等の安全パラメータを導入して無限ループや異常データを防止。

  - ETL パイプライン (pipeline)
    - ETLResult データクラスを公開（ETL の実行結果集約、品質問題・エラーの集約、辞書変換ユーティリティ含む）。
    - ETL モジュールのユーティリティ（テーブル存在チェック、最大日付取得、取引日調整など）を実装。
    - 差分取得・バックフィル・品質チェックを行う設計方針を取り入れた実装基盤を用意（jquants_client / quality モジュールと連携する想定）。
  - etl.py から ETLResult を再エクスポート（公開インターフェース整備）。

- 研究・因子 (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR / 相対 ATR、20日平均売買代金、出来高比率等のボラティリティ・流動性指標を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB SQL を活用し、営業日スキャンのバッファや欠損扱い等を考慮した実装。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得するクエリを実装。horizons のバリデーションあり。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算（欠損排除・有効レコード閾値あり）。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- AI / NLP (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp)
    - raw_news + news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信。
    - チャンク単位処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの最大記事数・最大文字数制限を実装してトークン膨張を防止。
    - 再試行ポリシー（429・ネットワーク断・APITimeout・5xx の指数バックオフ、最大リトライ回数）を実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code と score の検証、未知コードは無視、スコアを ±1.0 にクリップ）。
    - 成功分のみ ai_scores テーブルへ冪等的に書き換え（対象コードで DELETE → INSERT を実行し部分失敗耐性を確保）。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。api_key が未提供かつ環境変数 OPENAI_API_KEY 未設定の場合は ValueError。

  - 市場レジーム判定 (regime_detector)
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window により抽出された時間窓のタイトルを LLM に渡して評価。
    - LLM 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）で、同様にリトライ / フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - 計算結果は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。api_key 未指定時は環境変数 OPENAI_API_KEY を使用。

### Security
- 現時点で特別なセキュリティ修正はありません。API キー等の機密情報は環境変数経由で管理する設計（.env を利用する場合でも OS 環境変数優先）。

### Design / Safety notes
- ルックアヘッドバイアス防止:
  - 各所で datetime.today() / date.today() を直接参照しない設計（target_date ベースでの再現性を重視）。
  - prices_daily のクエリは target_date 未満 / between 条件でルックアヘッドを防止。
- DuckDB 互換性:
  - executemany の空リスト制約やリスト型バインドの互換性を考慮した実装（個別 DELETE の採用等）。
- フェイルセーフ:
  - OpenAI API 呼び出し失敗時は例外を投げずスコア算出へフォールバック（ゼロやスキップ）する箇所があるため、バッチ処理継続性が確保されています。
- ログ出力:
  - 重要な分岐・警告・情報はロギングされる設計（logger を各モジュールで使用）。

### Removed
- なし（初回リリース）

### Deprecated
- なし

### Fixed
- なし

---

注: 本 CHANGELOG はソースコードから推測して作成しています。実運用や将来のリリースでは、実際の変更差分に基づいて詳細を更新してください。