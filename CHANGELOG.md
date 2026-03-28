# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。主要サブパッケージ（data, strategy, execution, monitoring）を __all__ にてエクスポート。
- 環境設定管理 (kabusys.config)
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を探索）。
  - .env パーサー実装:
    - 空行・コメント行対応、`export KEY=val` 形式対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの取り扱い（クォート有無での差分処理）。
  - .env 読み込み時の上書き制御 (`override` と `protected`)、OS 環境変数保護。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で使用可能）。
  - Settings クラスを追加し、以下の設定プロパティを提供：
    - J-Quants / kabuステーション / Slack / データベースパス（DuckDB/SQLite） / 環境（development/paper_trading/live）/ ログレベル。
  - 必須環境変数未設定時に明確な ValueError を送出する `_require` 実装。
  - env・log_level の値検証（許容値リスト）を実装。

- ニュース NLP（AI）モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとの記事をまとめて OpenAI（gpt-4o-mini）へ送信してセンチメントスコアを算出。
    - チャンク処理（1コール最大 20 銘柄）・1 銘柄あたりの記事数/文字数制限（デフォルト: 10件/3000文字）。
    - JSON Mode を利用したレスポンス検証と堅牢なバリデーション（results 配列・code・score の検査、スコアの ±1.0 クリップ）。
    - ネットワーク断・429・タイムアウト・5xx に対する指数バックオフリトライ実装（最大リトライ回数設定）。
    - DB への書き込みは冪等（DELETE → INSERT）で、部分失敗時に他銘柄データを保護する戦略。
    - ルックアヘッドバイアス回避のため、内部で datetime.today()/date.today() を直接参照しない設計。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロニュース抽出は news_nlp.calc_news_window を使用（ウィンドウは前日 15:00 JST 〜 当日 08:30 JST 相当）。
    - OpenAI 呼び出しの独立実装（モジュール間のプライベート関数共有を回避）。
    - API エラー時のフェイルセーフ（macro_sentiment=0.0）やリトライロジックを実装。
    - DB 書き込みはトランザクションで冪等（BEGIN / DELETE / INSERT / COMMIT）に対応。
    - レジーム合成ロジック（スコアクリップ、閾値に基づくラベリング）を提供。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理：market_calendar テーブルを利用した営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - データ未取得時は曜日（平日＝営業日）ベースでフォールバックする堅牢設計。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等に更新する夜間バッチ処理を実装（バックフィル／健全性チェックあり）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー等の集約）。
    - 差分更新・バックフィル日数管理・品質チェック方針に基づく ETL 基盤のユーティリティを実装。
    - 内部ユーティリティ: テーブル存在チェック、テーブル最大日付取得などを実装。
  - etl モジュールは ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン／200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）などのファクター計算関数を実装。
    - 全関数は DuckDB 接続を受け取り prices_daily / raw_financials のみを参照（発注等のサイドエフェクトなし）。
    - SQL ウィンドウ関数を多用し、データ不足時の None 扱いを明確にした実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns: 柔軟な horizons 引数、入力検証）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンランク相関、データ不足時は None）。
    - rank ユーティリティ（同順位の平均ランク処理、丸めによる ties 対策）。
    - factor_summary（count/mean/std/min/max/median）やその他統計ユーティリティ。
  - research パッケージは主要関数を __all__ でエクスポート。

- その他
  - 外部依存（実装）に関する設計注記: OpenAI クライアント（OpenAI SDK）・duckdb を利用する前提。
  - 各モジュールでログ出力・警告処理を適切に行うことで運用時のトラブルシュートを容易に。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注記・設計方針（抜粋）
- ルックアヘッドバイアス回避: すべての「日付基準」関数は内部で date.today()/datetime.today() を直接参照しない設計。外部から target_date を注入する方式を採用。
- DB 書き込みは可能な限り冪等操作（DELETE→INSERT、ON CONFLICT 等）を行い、部分失敗時のデータ保護を重視。
- OpenAI への問い合わせは JSON Mode を利用し、厳密なレスポンス検証と堅牢なリトライロジックを実装。
- 外部 API 呼び出しでのフェイルセーフ（API 失敗時はスキップまたは中立値にフォールバック）により、ETL/解析ジョブの継続性を保つ設計。

将来的な変更点（予定）
- strategy / execution / monitoring の具体的取引ロジックと発注実装の追加（本リリースではデータ収集・分析・ユーティリティを中心に実装）。
- ai モデルやプロンプトの改善、OpenAI SDK のバージョン互換性検証。
- テストカバレッジ強化とエンドツーエンド CI ワークフローの整備。

--- 

この CHANGELOG はコードベース（src/kabusys 以下）から推定して作成しています。実際のリリースノート作成時はテスト結果・マニュアル変更点・リリース手順等を合わせて更新してください。