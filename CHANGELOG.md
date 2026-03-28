# Changelog

すべての変更は Keep a Changelog の仕様に準拠し、セマンティックバージョニングを使用しています。  
このファイルは、コードベースから推測される機能追加・設計方針・重要な実装上の注意点をまとめたものです。

## [Unreleased]

- ドキュメント／設計ノートの追加やリファクタリング予定：
  - テストカバレッジの拡充（OpenAI コールのモック化・DuckDB 周りの集積テスト）。
  - パフォーマンスプロファイリング（大規模ニュースバッチ処理／ETL 実行時）。
  - エラーメトリクスや監視（Slack 通知等）の統合。

## [0.1.0] - 2026-03-28

Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎モジュール群を追加。
  - パッケージの公開情報
    - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を定義。
    - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に設定。
  - 環境設定 / ロード
    - src/kabusys/config.py
      - .env / .env.local 自動ロード機能を実装（プロジェクトルートを .git or pyproject.toml で探索）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
      - .env パーサ実装: export プレフィックス、シングル/ダブルクォートやバックスラッシュエスケープ、インラインコメントの扱いに対応。
      - 環境変数保護（OS 環境変数を protected として上書き抑止）。
      - Settings クラスを提供し、必須値取得（_require）や各種設定プロパティ（J-Quants / kabuStation / Slack / DB パス / 環境 / log level 等）を公開。
      - KABUSYS_ENV, LOG_LEVEL のバリデーションを実装。is_live / is_paper / is_dev のヘルパーを提供。
  - AI（NLP）モジュール
    - src/kabusys/ai/news_nlp.py
      - raw_news / news_symbols を銘柄単位に集約し、OpenAI（gpt-4o-mini）でバッチ（最大 20 銘柄/チャンク）センチメント解析して ai_scores テーブルへ書き込み。
      - 時間ウィンドウ計算（JST 前日 15:00 〜 当日 08:30 を UTC に変換）を calc_news_window で提供。
      - トークン肥大化対策（最大記事数／最大文字数でトリム）、JSON mode を用いた応答フォーマットと堅牢なレスポンス検証ロジックを実装。
      - エラー耐性: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。その他エラー時は個別チャンクをスキップして継続。部分書き込みを避けるため DELETE → INSERT の置換ロジックを採用。
      - DuckDB 互換性配慮: executemany に空リストを渡さないチェックを実装（DuckDB 0.10 の制約回避）。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を組み合わせて日次で market_regime を判定・保存。
      - マクロ記事抽出（キーワードリスト）→ OpenAI 呼び出し（gpt-4o-mini）→ スコア合成（clip）→ market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - API キー注入（引数優先、環境変数 OPENAI_API_KEY のフォールバック）、API エラー時は macro_sentiment=0.0 でフェイルセーフ継続。
  - Research / ファクター計算
    - src/kabusys/research/factor_research.py
      - モメンタム（約1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金／出来高比率）、バリュー（PER/ROE）などのファクター計算関数を提供。
      - DuckDB を用いた SQL ベースの実装。結果は (date, code) をキーとする辞書リストで返却。
      - データ不足時の None ハンドリングを明示。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（複数ホライズン）、IC（Spearman ρ）計算、ランク関数（同順位は平均ランク）およびファクター統計サマリー機能を提供。標準ライブラリのみで実装。
  - Data プラットフォーム関連
    - src/kabusys/data/calendar_management.py
      - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB の登録値を優先し、未登録日は曜日ベースでフォールバックする一貫性ロジックを持つ。
      - calendar_update_job により J-Quants API から差分取得し冪等に保存。バックフィルや健全性チェック（過度に未来の last_date を検出した際のスキップ）を実装。
    - src/kabusys/data/pipeline.py / etl.py
      - ETLResult データクラスで ETL 実行結果を集約（取得数・保存数・品質問題・エラーリスト等）。
      - 差分取得・保存・品質チェックの流れを想定した ETL ユーティリティ（J-Quants クライアント jquants_client と quality モジュールを連携する設計）。
      - 設計上の配慮点として、backfill、最大取得日管理、品質チェックは致命的エラーでも処理を継続して結果を収集する方針。
  - 基盤的な実装慣行
    - ルックアヘッドバイアス防止: 日時計算において datetime.today()/date.today() を直接参照しない（target_date を明示的に与える設計）。
    - DB 書き込みは冪等性を重視（DELETE → INSERT など）。
    - OpenAI 呼び出しのテスト容易性を考慮し、内部呼び出し関数を patch 可能に設計（モジュール間で private 関数を共有しない方針）。
    - ロギングや警告を随所に実装し、フェールセーフのデフォルト値（例: ma200_ratio=1.0、macro_sentiment=0.0）を定義。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数による注入をサポートし、環境変数（OPENAI_API_KEY）をフォールバックとして使用。環境変数の管理と自動ロードは慎重に扱われ、OS 環境変数上書き防止機構を備える。

Notes / Implementation Caveats
- DuckDB のバージョン差異に起因する制約（executemany に空リストを渡せない等）に対応するガードを実装していますが、実行環境の DuckDB バージョンによっては追加調整が必要になる可能性があります。
- OpenAI のレスポンスは厳密な JSON を期待していますが、稀に前後に付加テキストが混入するケースに備えたパーシングの回復処理を含めています。
- news_nlp / regime_detector 共に LLM 呼び出しに依存するため、API レート制限や応答品質が結果に影響を与えます。ロギングとリトライ機構により安定化を図っていますが、運用時には API 利用状況の監視を推奨します。

---

作成にあたっては、ソースコード内の docstring／コメント、関数署名、設計方針の注記から主要機能・振る舞いを推測して記載しました。追加のリリース履歴や日付の変更、より細かな変更点（バグ修正・微改善など）を反映したい場合は、具体的なコミット履歴や差分を提供してください。