# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠し、安定した API を維持するための変更履歴を分かりやすく記載します。

## [Unreleased]

（現在リリース予定の変更はありません）

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティ群を一通り実装しています。以下の機能と設計方針を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期リリース。バージョンは 0.1.0。
  - パブリックサブパッケージとして data, research, ai, execution, monitoring, strategy などを想定したエクスポートを用意。

- 環境設定 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数からの設定読み込み機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を探す）により CWD に依存しない自動ロードを実行。
  - .env のパースは以下をサポート:
    - 空行・コメント行（先頭 #）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無し値のインラインコメント処理（'#' の直前が空白またはタブの場合にコメント扱い）
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - protected（既存 OS 環境変数）を尊重する上書きロジック（.env.local は上書き、.env は未設定のみセット）。
  - Settings クラスを提供し、必要な設定項目（J-Quants / kabu / Slack / DB パス等）をプロパティで取得。未設定時は ValueError を送出。
  - KABUSYS_ENV / LOG_LEVEL の値検証とユーティリティプロパティ（is_live / is_paper / is_dev）。

- データプラットフォーム (src/kabusys/data/)
  - ETL パイプライン基盤（pipeline.py）
    - ETLResult データクラスを公開（etl モジュール経由で再エクスポート）。
    - 差分取得、バックフィル(デフォルト 3 日)、品質チェック用の結果収集ロジックを意識した設計。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを実装。
  - カレンダー管理（calendar_management.py）
    - market_calendar を用いた営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行う一貫した挙動。
    - 夜間バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック）。
    - 最大探索日数やバックフィル、先読み日数等の安全装置を実装。

  - ETL ユーティリティ公開インターフェース（etl.py）で ETLResult を再エクスポート。

  - DuckDB の互換性や制約（executemany に空リスト不可など）を考慮した実装。

- AI / NLP 機能 (src/kabusys/ai/)
  - ニュース NLP（news_nlp.py）
    - raw_news / news_symbols から記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ保存。
    - 時間ウィンドウは「前日 15:00 JST ～ 当日 08:30 JST」を UTC に変換して使用（ルックアヘッド対策）。
    - チャンクバッチ（デフォルト 20 銘柄）での API 呼び出し、最大記事数・文字数トリムによるトークン制御。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。その他エラーはスキップして継続（フェイルセーフ）。
    - JSON Mode のレスポンス検証と復元処理（前後余計なテキストが混ざる場合の {} 抽出）。
    - スコアは ±1.0 にクリップ。レスポンスの検証に失敗した場合は当該チャンクをスキップ。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
    - DuckDB へは部分更新（該当 code の DELETE → INSERT）を行い、部分失敗時に他銘柄の既存データを保護。

  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - MA 比率の計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロニュース抽出はキーワードによるフィルタリング（日本・米国関連等）。
    - OpenAI 呼び出しは独立実装で、失敗時は macro_sentiment=0.0 として継続するフェイルセーフを採用。
    - 合成スコアはクリップ処理と閾値によるラベリングを実施。
    - market_regime テーブルへは冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を実装。

- 研究用ユーティリティ (src/kabusys/research/)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高比率）、Value（PER, ROE）などのファクター計算関数を実装。
    - DuckDB ベースの SQL 実行により、prices_daily / raw_financials を参照して結果を (date, code) キーの dict リストで返す設計。
  - feature_exploration.py
    - 将来リターン計算（指定ホライズンに対する LEAD を用いる）、IC（Spearman のランク相関）計算、ランク変換、ファクター統計サマリを実装。
    - 外部依存を持たない標準ライブラリのみの実装。horizons の検証やランクの同順位処理を明示的に実装。
  - research パッケージは便利関数を __all__ で公開。

### 変更 (Changed)
- このリリースは初版のため、API や挙動の設計方針を確定して導入（詳細は各モジュールの docstring を参照）。

### 修正 (Fixed)
- N/A（初回リリース）。

### セキュリティ (Security)
- OpenAI API キーを直接要求し、未設定時は明確な ValueError を送出することで誤った呼び出しを防止。
- 環境変数の保護（protected set）により OS 側の重要な環境変数を .env による上書きから守る仕組みを採用。

### 設計上の重要な注意点（ドキュメント）
- すべての時刻関連ロジックはルックアヘッドバイアスを避けるため、datetime.today() / date.today() を直接参照しない設計（target_date を明示的に渡す）。
- 外部 API の失敗はフェイルセーフ（中立値やスキップ）で処理を継続する設計。監査用ログは残すが、単一 API 障害でパイプライン全体が停止しないようにしている。
- DuckDB のバージョン差異（executemany の空リスト制約等）を考慮した実装になっているため、運用環境の DuckDB バージョンに留意すること。

---

今後のリリースでは、実運用向けの監視・発注モジュール（execution / monitoring / strategy）の実装拡張、テストカバレッジ強化、性能最適化、及び外部 API クライアント（kabu / jquants）の具体的実装を予定しています。