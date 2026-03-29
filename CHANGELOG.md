Changelog
=========

すべての重要な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」スタイルに準拠しています。

0.1.0 - 2026-03-29
------------------

Added
- 初回リリース: KabuSys 日本株自動売買/リサーチ基盤のコア機能群を追加。
  - パッケージ構成:
    - kabusys (パッケージトップ): バージョン管理と主要サブパッケージの公開（data, research, ai 等）。
  - 設定/環境管理:
    - 環境変数読み込みモジュールを追加（kabusys.config）。
    - .env / .env.local 自動ロード（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ。
    - .env パーサーは export プレフィックス、クォート処理、インラインコメント等に対応。
    - OS 環境変数保護（既存の環境変数を protected として上書きを防止）。
    - Settings クラスで型付きプロパティを提供（J-Quants / kabu API / Slack / DB パス / 環境判定 / ログレベル等）。
    - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
  - データプラットフォーム:
    - カレンダー管理（kabusys.data.calendar_management）
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
      - market_calendar DB の有無に応じた「DB優先・未登録は曜日フォールバック」ロジック。
      - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック）。
    - ETL パイプライン（kabusys.data.pipeline / etl）
      - 差分更新・バックフィル・品質チェックのためのユーティリティ。
      - ETLResult データクラスを公開（取得／保存件数、品質問題、エラー集約など）。
      - DuckDB 互換性のための実装注意（テーブル存在チェック、MAX date 取得等）。
    - jquants_client 用フック（jquants_client との連携想定、保存処理は idempotent を想定）。
  - リサーチ/ファクター:
    - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
      - 1M/3M/6M リターン、MA200 乖離、ATR20、流動性指標、PER/ROE 等を DuckDB SQL で算出。
      - 欠損・データ不足時の None ハンドリング。
    - 特徴量探索（kabusys.research.feature_exploration）
      - calc_forward_returns（任意ホライズンの将来リターン算出、horizons バリデーション）
      - calc_ic（ファクターと将来リターンのスピアマンランク相関）
      - rank（同順位は平均ランクで処理）
      - factor_summary（count/mean/std/min/max/median を算出）
    - zscore_normalize の re-export（kabusys.research から kabusys.data.stats 連携）。
  - AI / ニュース NLP:
    - ニュースセンチメントスコア生成（kabusys.ai.news_nlp）
      - news ウィンドウの計算（前日15:00 JST～当日08:30 JST 相当の UTC 範囲）。
      - raw_news と news_symbols から銘柄ごとに記事を集約（最大記事数・文字数でトリム）。
      - OpenAI（gpt-4o-mini）へのバッチ送信（1回最大 20 銘柄）。
      - レスポンスバリデーション（JSON 抽出・results リスト検証・コード/スコア検査）。
      - DuckDB の executemany 空リスト制約を考慮した安全な DELETE/INSERT ロジック。
    - 市場レジーム判定（kabusys.ai.regime_detector）
      - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成。
      - レジームラベル: bull / neutral / bear。
      - LLM 呼び出しは独立実装、レスポンスパース失敗やAPI失敗はフェイルセーフで macro_sentiment=0.0 にフォールバック。
  - OpenAI 統合共通:
    - gpt-4o-mini（JSON Mode）を使用し、API 呼び出しはリトライ（429/接続断/タイムアウト/5xx は指数バックオフ）を実装。
    - レスポンスパースに堅牢な処理（前後余計なテキストを含む JSON の復元等）。
    - テスト用に _call_openai_api の差し替えが可能（unittest.mock.patch を想定）。
  - ロギング / エラーハンドリング:
    - 各モジュールで詳細なログ出力（info/debug/warning/exception）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT を基本とし、例外時に ROLLBACK を試行。
    - API 呼び出し失敗時は基本的に例外を上位に投げずフェイルセーフで継続する設計（監視側で検知する方針）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロード時に OS 側の既存環境変数を上書きしない仕組みを導入（protected set）。
- OpenAI API キー未設定時は明確な ValueError を発生させることで誤構成を検出しやすくした。

Performance
- news_nlp のバッチサイズを導入（デフォルト 20 銘柄）し、API 呼び出し回数を削減。
- DuckDB 内でのウィンドウ関数活用により多数銘柄の一括処理を高速化。

Notes / Design decisions
- ルックアヘッドバイアス防止:
  - datetime.today() / date.today() を直接スコア算出やプロンプト作成に混入させない設計。全ての関数は target_date を明示受け取り、過去データのみ参照する。
- DuckDB のバージョン差異（executemany の空リスト取扱い等）に配慮した実装と互換性保護。
- idempotent な DB 書き込み（一旦削除してから挿入）により再実行可能な ETL / バッチ処理を実現。
- OpenAI レスポンスの堅牢なパースとフォールバックにより、API 側の不整合があってもシステム全体の継続運用を優先。

開発者向け補足
- テスト/モック: OpenAI 呼び出し部分（kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api）をパッチしてユニットテスト可能。
- 環境: .env.example を元に必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定すること。

今後の予定（例）
- ファクターの追加（PBR、配当利回り等）
- モデル学習 / バックテストのためのより豊富な研究ユーティリティ
- モニタリング／アラート機能の拡充（Slack 通知やメトリクス公開）

（注）本 CHANGELOG は提供されたソースコードから機能・設計意図を推測して作成しています。実際のリリースノートとは差異がある場合があります。