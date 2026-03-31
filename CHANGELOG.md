# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に準拠しており、セマンティックバージョニングを使用します。

## [Unreleased]

### 追加
- ドキュメントと内部設計に基づく多数のモジュール追加 / 実装整理（詳細は 0.1.0 の項目を参照）。
- テスト容易性を考慮したポイントを複数追加:
  - OpenAI 呼び出しの内部インターフェースを関数化して unittest.mock で差し替え可能にした。
  - API キーを引数注入できる設計（api_key 引数を受け取る関数群）。

### 変更
- なし（初期リリース以降の変更はここに記載）。

### 修正
- なし

---

## [0.1.0] - 2026-03-31

初期リリース。コードベースから推測できる主要機能と設計上の特徴を以下に記載します。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = "0.1.0"、主要サブパッケージを __all__ に公開）。

- 環境変数 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を読み込む。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export KEY=val 形式、引用符エスケープ、行末コメント等に対応。
    - OS 環境変数を保護するため protected set を使った上書き制御。
  - Settings クラスを提供（プロパティで必須値の検証やデフォルト値を提供）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - KABUSYS_ENV 値検証（development / paper_trading / live）。
    - LOG_LEVEL 値検証（DEBUG/INFO/...）。
    - DB パス（DuckDB/SQLite）の Path 型解決ユーティリティ。
    - is_live / is_paper / is_dev の簡易判定プロパティ。

- AI 関連 (`kabusys.ai`)
  - news_nlp モジュール
    - raw_news と news_symbols を集計して OpenAI（gpt-4o-mini, JSON mode）にバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ保存する処理を実装。
    - チャンク処理（最大 20 銘柄 / API コール）、1 銘柄あたり記事数最大 10 件、文字長制限あり。
    - タイムウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - API 失敗（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフリトライ。
    - レスポンス検証ロジック（JSON 抽出、results 配列、コード照合、スコア数値性検査、±1.0 でクリップ）。
    - DB への書き込みは部分失敗を避けるため、該当コードのみ DELETE → INSERT で置換（DuckDB 互換性考慮）。
  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - ma200_ratio 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロニュースは news_nlp の calc_news_window で定義されたウィンドウからマクロキーワードを含むタイトルを抽出。
    - OpenAI 呼び出しは独立した内部実装（モジュール結合を避ける）。
    - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
    - DB 書き込みはトランザクションで冪等（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK 実施。

- 研究・分析機能 (`kabusys.research`)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）等のファクター計算関数を実装。
    - DuckDB 上で SQL を駆使して効率的に集計。データ不足時の None 扱い。
  - feature_exploration
    - 将来リターンの計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient、Spearman ρ）計算（ランク変換・同順位は平均ランク）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
    - pandas 等の外部依存を持たない純標準ライブラリ + DuckDB 実装。

- データプラットフォーム (`kabusys.data`)
  - calendar_management
    - market_calendar テーブルを元に営業日判定、次/前営業日の算出、期間内営業日取得、SQ 日判定を提供。
    - DB のカレンダーデータがない場合は曜日ベース（平日）でフォールバック。
    - calendar_update_job による J-Quants API からの差分取得・保存（バックフィル、健全性チェック、例外処理）を実装。
    - 最大探索範囲やバックフィル日数などの保護機構を実装。
  - pipeline / etl
    - ETLResult dataclass と ETL パイプラインの骨格（差分更新、保存、品質チェックの呼び出しと結果集約）を実装。
    - DB 上の最終取得日時探索、最小ロード日管理、バックフィルのデフォルト値。
    - 品質チェック（quality モジュールを利用）結果を ETLResult に集約し、致命的エラーの有無判定を提供。
  - jquants_client など外部クライアントモジュールを想定した設計（fetch / save の抽象化）。

### 変更
- なし（初期リリース）。

### 修正 / フェイルセーフ実装
- OpenAI / 外部 API 呼び出しでのさまざまな障害（429, network, timeout, 5xx）に対してリトライとログ、最終失敗時の安全なフォールバック（マクロセンチメント = 0.0、スコア取得失敗はスキップ）を実装。
- DuckDB への書き込みはトランザクション制御（BEGIN/COMMIT/ROLLBACK）で保護。ROLLBACK 失敗時は警告ログを出力。
- データ不足時の既知の挙動を明確化:
  - ma200_ratio が計算できない場合は中立値 1.0 を採用して処理継続。
  - ニュース記事がない場合は LLM 呼び出しを行わず 0 件扱い。
  - ファクター計算でデータ不足の銘柄は None を返す。

### セキュリティ
- 環境変数読み込みで OS 環境変数を保護する設計（.env による上書きを制御）。
- API キーは環境変数または引数注入で扱い、明示的に未設定を検出して ValueError を発生させる（誤動作を早期に検出）。

### 既知の制限 / 注意事項
- OpenAI クライアントは gpt-4o-mini / JSON mode を前提としているため、将来の API 変更に対する互換性確認が必要。
- DuckDB の executemany に空配列を渡せない制約に対応するコードが含まれる（バージョン依存性に注意）。
- タイムゾーン扱いは UTC naive datetime を用いており、JST ↔ UTC の変換ロジックを明示的に使用している。外部との時間取り扱いに注意。
- 一部の外部クライアント関数（jquants_client など）は実装を想定しているため、本パッケージ単体で全ての機能が動作するわけではない。

---

著者: コードベースから推測して作成  
（必要であれば各リリース項目を詳細化したり、実際の変更ファイル / コミットログに合わせて日付・内容を修正してください）