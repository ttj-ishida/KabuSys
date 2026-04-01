# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成した初期の変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 今後の改善案（推奨）
  - OpenAI クライアント初期化の DI（テスト容易化）やレスポンスのより厳密なスキーマ検証
  - DuckDB ベースのクエリ最適化や大規模データ向けのバッチ処理最適化
  - ETL の品質チェックから自動通知（Slack 等）への連携
  - calendar_update_job / ETL のサンプル運用スケジュール（cron / ワークフロー）のドキュメント追加

---

## [0.1.0] - 2026-04-01

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ定義: src/kabusys/__init__.py にバージョンと主要サブパッケージのエクスポート定義を追加（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
      - プロジェクトルート検出（.git または pyproject.toml を起点）により CWD に依存しない自動ロード。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - 強力な .env 行パーサ（export 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの処理）。
    - override / protected オプション付きで .env を安全に読み込む実装。
    - Settings クラスを提供し、必須設定取得メソッド（_require）と以下のプロパティを定義:
      - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite） / 監視閾値（CPU/Memory/Disk） / ログレベル / 実行環境判定（development/paper_trading/live）。

- AI モジュール（OpenAI を用いたニュース解析 / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む処理を実装。
    - 特徴:
      - JST 時間ウィンドウの厳密な計算（前日 15:00 JST 〜 当日 08:30 JST）とそれに対応する UTC naive datetime の使用。
      - 1銘柄あたりの記事数・文字数の上限（トークン肥大化対策）。
      - バッチ処理（最大 20 銘柄 / API コール）とエクスポネンシャルバックオフを伴うリトライ（429/ネットワーク/5xx/タイムアウト対応）。
      - レスポンスのバリデーションとスコアの ±1 クリップ。
      - 部分成功時に既存の ai_scores を保護するため、書き込みは対象コードに限定して DELETE → INSERT を冪等に実行。
      - テストしやすいように _call_openai_api を分離（unittest.mock.patch で差し替え可能）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込む処理を実装。
    - 特徴:
      - DuckDB からの過去データ取得でルックアヘッドを防止（date < target_date 等）。
      - マクロキーワードで raw_news をフィルタし、最大件数を上限に LLM に渡す。
      - OpenAI 呼び出しは独立した実装でモジュール結合を避ける設計。
      - API エラー/パース失敗時は安全側（macro_sentiment = 0.0）にフォールバックし継続。
      - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）と失敗時の ROLLBACK 保護ログ。

- データプラットフォーム / ETL
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass を導入し、ETL の取得・保存件数、品質チェック結果、エラーなどを集約するインターフェースを提供。
    - 差分取得・バックフィル・品質チェックを想定した設計（J-Quants API を用いる想定）。
    - DuckDB テーブル存在確認や最大日付取得などの内部ユーティリティ。
  - src/kabusys/data/etl.py
    - pipeline の ETLResult を再エクスポートし公開インターフェースを提供。

- マーケットカレンダー管理
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）を実装（J-Quants クライアント経由で差分取得→save）。
    - 営業日判定ユーティリティ群を提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - 設計上のポイント:
      - market_calendar が未取得の時は曜日ベースのフォールバック（週末は非営業日）。
      - DB に登録済みデータを優先し、未登録日は曜日フォールバックで一貫性を担保。
      - 最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止。
      - カレンダー更新ではバックフィルと健全性チェックを実装。

- Research（因子計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン・200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER/ROE）などのファクター計算を実装。
    - DuckDB SQL を主体に、データ不足時には None を返すよう設計（安全）。
    - 関数: calc_momentum, calc_volatility, calc_value（いずれも target_date ベースで date/code 単位の結果を返す）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターンの計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランキング変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - スピアマンランク相関のためのランク変換（同順位は平均ランク）実装や数値フィルタリングを含む。
  - src/kabusys/research/__init__.py に主要関数をエクスポート。

- データユーティリティ
  - src/kabusys/data/calendar_management.py, pipeline.py 等で DuckDB を前提とした堅牢な SQL + Python 混合実装を採用。
  - jquants_client 依存箇所はクライアントモジュール（kabusys.data.jquants_client）経由の呼び出しを想定。

Security / Reliability
- OpenAI 呼び出しに対してリトライ / バックオフを実装し、API 側の一時エラーに耐性を持たせる設計。
- 外部 API 欠落・失敗時は例外の暴発を避け、フェイルセーフ（ゼロスコアやスキップ）で継続する実装。
- DB 書き込みは冪等性（DELETE→INSERT、ON CONFLICT など）やトランザクションで保護。

Notes / Known limitations
- OpenAI レスポンスは JSON Mode を利用するが、現実的には余計な前後テキストが混在する場合があるためパース時に最外の {} を抽出する復元処理を実装している。これでも完全ではないため将来的により強固なスキーマ検証が望ましい。
- ETL / calendar_update_job は外部 J-Quants クライアント（jquants_client）に依存する。テストや CI ではモックまたはサンプルデータが必要。
- DuckDB executemany の挙動（空リスト不可など）に依存するため、実行前にパラメータ空チェックを行っている。
- このリリースでは一部の PBR / 配当利回り等のバリューファクターは未実装（将来の拡張対象）。

---

作成者注:
- 本 CHANGELOG は提供されたソースコード内容から機能・設計方針を推測して記載しています。実際のリポジトリ履歴（コミット単位の変更履歴）と異なる場合があります。必要であればコミットログやリリースノートに合わせて調整してください。