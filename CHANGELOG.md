# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

なお、本 CHANGELOG はコードベース（src/kabusys 以下）から実装内容を推測して作成しています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ初期リリース:
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージルートでの公開: __all__ により data, strategy, execution, monitoring を公開。

- 設定管理 (`kabusys.config`):
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索するため、CWD に依存しない読み込みを実現。
  - .env パーサーを実装:
    - コメント行・空行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく扱う。
    - クォートなしの値ではインラインコメント判定（'#' の直前が空白/タブの場合のみ）に対応。
  - .env 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス /環境 (development/paper_trading/live) /ログレベルの取得と検証を実装。
  - 環境変数未設定時に明示的に ValueError を送出する _require 関数を提供。

- データ層 (`kabusys.data`):
  - ETL パイプライン用データクラス ETLResult を公開（kabusys.data.etl で再エクスポート）。
  - pipeline モジュールにより差分取得・保存・品質チェックを行う基本骨格を実装（DuckDB を使用）。
  - calendar_management モジュールを実装:
    - JPX カレンダー (market_calendar) の夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - カレンダーデータが未取得の場合は曜日ベースのフォールバック（週末は非営業日）を行う設計。
    - 最大探索日数制限やバックフィル、健全性チェックを導入して無限ループや異常データを防止。

- 研究・分析モジュール (`kabusys.research`):
  - factor_research モジュールを実装:
    - モメンタム (1M/3M/6M リターン, 200日移動平均乖離)、ボラティリティ（20日 ATR）、流動性指標（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials を参照して計算。
    - データ不足時の None 処理やログ出力を実装。
  - feature_exploration モジュールを実装:
    - 将来リターン calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - ランク相関（Spearman）に基づく IC 計算 calc_ic。
    - ランク付けユーティリティ rank（同順位は平均ランク）。
    - ファクター統計 summary を取得する factor_summary。
  - 研究系関数をトップレベルで再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- AI（NLP）モジュール (`kabusys.ai`):
  - ニュースセンチメント分析（score_news）:
    - raw_news と news_symbols を集約し、銘柄ごとに最新記事をまとめて OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントスコアを取得。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST の記事を対象（UTC に変換して DB と比較）。
    - 1チャンクあたり最大20銘柄、1銘柄あたり最大10記事・3000文字でトリムする対策を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンスの厳格なバリデーション（JSON 抽出、results の存在/型、code の検証、数値変換、スコアのクリップ）を実装。
    - 取得したスコアは ai_scores テーブルへトランザクション（DELETE → INSERT）で書き込み。部分失敗時に他コードの既存スコアを保護する実装。
    - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch で置換可能）。
  - 市場レジーム判定（score_regime）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込み。
    - マクロニュースは raw_news からマクロキーワードで抽出（最大 20 件）。OpenAI 呼び出しは専用実装でモジュール結合を避ける。
    - LLM エラーやパース失敗時は macro_sentiment=0.0 とするフェイルセーフを実装。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。ただし実装上のフォールバックやフェイルセーフ動作（API 失敗時の0フォールバック、DB 書き込み時の ROLLBACK ハンドリングなど）を明記。

### 内部（Internal / Notes）
- 全モジュールでルックアヘッドバイアスを避けるため、datetime.today() / date.today() を直接参照しない設計方針を採用。関数は target_date を明示的に受け取る。
- DuckDB を主要なローカル DB として使用。SQL と Python の組合せで高性能に集計・ウィンドウ計算を行う実装。
- OpenAI SDK の使用に際して、APIError の status_code 存在有無に対応する安全な扱いを実装。
- ログを活用した可観測性（logger.info / warning / exception）を各処理に実装。
- テストしやすさを考慮し、外部 API 呼び出し点（OpenAI クライアント呼び出し、jquants_client など）を差し替え可能にしている。

### 既知の制約 / 今後の課題
- PBR や配当利回りなどのバリューファクターは未実装（calc_value の注記参照）。
- news_nlp と regime_detector は同様の OpenAI 呼び出しロジックを持つが、モジュール間でプライベート関数を共有しない設計（意図的）。
- DuckDB executemany に関するバージョン互換性のため、空リストの扱いに注意したガードを実装している。将来的に DuckDB バージョン依存を整理予定。

---

今後のリリースでは、機能拡張（発注ロジック、モニタリング UI、より多くのファクタ類）、テストカバレッジ向上、OpenAI 呼び出しの抽象化・共有、ドキュメント整備等を予定しています。