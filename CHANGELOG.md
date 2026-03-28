# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

今後のリリースでは、各バージョンの追加・変更点をここに追記してください。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを実装。パッケージバージョンは 0.1.0。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を __all__ で定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート探索: __file__ を基点に .git または pyproject.toml を探索して自動読み込みを行う（CWD に依存しない）。
  - .env パース実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - .env の読み込み順序: OS 環境変数 > .env.local > .env。OS の既存環境変数は保護（protected）される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト等で有用）。
  - Settings クラスを実装し、アプリケーション設定値（J-Quants トークン、kabu API、Slack、DB パス、環境・ログレベル判定など）をプロパティで提供。
  - 環境変数値の検証: KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装し、不正値時に ValueError を送出。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を評価し ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（JST ベース、前日 15:00 ～ 当日 08:30）計算関数 calc_news_window を提供。
    - バッチ処理: 最大 20 銘柄単位のチャンク送信、1 銘柄当たりの記事数・文字数上限（トリム）の制御を実装。
    - JSON mode を利用したレスポンス処理と堅牢なバリデーション（JSON 抽出、results キー検査、スコア型チェック、±クリップ）。
    - 再試行ロジック: 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフによるリトライ。その他エラーはスキップして継続（フェイルセーフ）。
    - DuckDB に対する互換性配慮（executemany の空リスト回避、部分更新で既存データ保護）。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api を通じて抽象化し、ユニットテストで差し替え可能。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - ma200_ratio 計算はルックアヘッドを防ぐため target_date 未満のデータのみ使用し、データ不足時は中立（1.0）でフォールバック。
    - マクロニュース抽出は定義済キーワード群でフィルタし、最大件数制限あり。
    - OpenAI 呼び出し（gpt-4o-mini）に対するリトライ・バックオフ・エラーハンドリングを実装。API 失敗時は macro_sentiment=0.0 で継続する（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。失敗時は ROLLBACK を試行し例外を上位へ伝播。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュールを実装:
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算（データ不足時は None）。
    - ボラティリティ: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー: raw_financials から直近財務を結合して PER・ROE を計算（EPS が 0 または NULL の場合 PER は None）。
    - DuckDB による SQL ベースの実装で外部 API への依存なし。
  - feature_exploration モジュールを実装:
    - 将来リターン calc_forward_returns（任意 horizon、デフォルト [1,5,21]）、リードによる取得。
    - IC 計算（Spearman の ρ） calc_ic、ランク変換ユーティリティ rank、ファクター統計要約 factor_summary を実装。
    - 標準ライブラリのみで動作する設計。

- データプラットフォーム (kabusys.data)
  - calendar_management
    - JPX カレンダーを扱うユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベース（平日＝営業日）でフォールバックするロジックを実装し、DB 登録値優先と未登録日の一貫した扱いを提供。
    - calendar_update_job: J-Quants API から差分取得 → 保存（冪等）する夜間バッチ処理を実装。バックフィルと健全性チェックを組み込み。
  - ETL / pipeline
    - ETLResult データクラスを公開し、ETL 実行結果（取得件数、保存件数、品質問題、エラー要約など）を集約して返す仕組みを導入。
    - pipeline モジュールは差分取得、保存（jquants_client 経由の冪等保存）、品質チェック（quality モジュール）を想定した設計。初回ロード用の最小日付やバックフィル日数等の定数を定義。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- 互換性 / テスト配慮
  - OpenAI 呼び出し箇所でテスト時に置き換え可能な内部ラッパーを使用（_call_openai_api をパッチ可能）。
  - DuckDB のバージョン依存（executemany の空リスト不可等）への対応を実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 既知の制約・注意点 (Notes)
- OpenAI API の利用には環境変数 OPENAI_API_KEY の設定が必要（各関数は引数 api_key を受け取り、未指定時は環境変数を参照）。未設定時は ValueError を送出する。
- DuckDB を利用するため、動作確認には DuckDB を使用可能な環境が必要。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる（パッケージ配布後の挙動を考慮）。
- 一部設計はフェイルセーフ（API 失敗時はスキップして継続）を優先しており、運用観点でログ監視やリトライ設定の調整が必要となる場合がある。
- JSON mode を利用するが、LLM の不整形出力（前後の余計なテキスト等）に対する耐性処理を実装しているものの、極端に逸脱した出力が返るケースは完全には除去できないため運用上の監視を推奨。

---

開発者・運用者は ISSUE や PR にて改善点やバグ報告、機能追加要望をお寄せください。