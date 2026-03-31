Keep a Changelog
=================
すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

[unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0

0.1.0 - 2026-03-31
------------------

Added
- パッケージ基盤
  - 初期パッケージ kabusys を追加。パッケージの公開バージョンは 0.1.0（src/kabusys/__init__.py で定義）。
  - パブリックサブパッケージのエクスポートを定義（data, research, ai, 等の主要モジュール群を想定）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの自動検出は .git または pyproject.toml を基準に行うため、CWD に依存しない設計。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - .env パーサ実装:
    - コメント行、export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメントの取り扱いに対応。
  - Settings クラスでアプリケーション固有設定を公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DB パス, 監視閾値, 環境切替等）。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
    - Path 型を返すプロパティは expanduser を行う（相対パスや ~ の扱いを明確化）。
    - 必須値未設定時は ValueError を送出。

- AI ニュース解析 (src/kabusys/ai)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメント（-1.0〜1.0）を算出する処理を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事数・文字数上限、レスポンス検証、スコアクリップ（±1.0）を実装。
    - エラーに対してはフェイルセーフ（API失敗時は該当チャンクをスキップし続行）、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - JSON パース失敗時の復元ロジック（非純粋な出力から最外の {} を抽出）やレスポンス検証ロジックを実装。
    - テスト容易性のため、内部で OpenAI 呼び出し関数を patch 可能 (*.news_nlp._call_openai_api*) に設計。
    - score_news 関数は target_date に対応した JST ベースの収集ウィンドウ計算（calc_news_window）を提供し、DuckDB への書き込みは冪等化（DELETE→INSERT を実行）する。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - 日次で市場レジーム（bull/neutral/bear）を判定するロジックを実装。
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせてレジームスコアを算出。
      - OpenAI 呼び出しを行う際のリトライ・例外ハンドリング、API 失敗時のフォールバック (macro_sentiment=0.0) を考慮。
      - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼出しは news_nlp と独立した実装でモジュール結合を避ける設計。

- データ基盤ユーティリティ (src/kabusys/data)
  - calendar_management モジュール
    - JPX 市場カレンダーの管理・夜間バッチ取得（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定 API を提供。
    - market_calendar が存在しない場合は曜日ベースのフォールバック（週末を非営業日扱い）、DB の部分的登録に対しても一貫した挙動を実現。
    - 更新時のバックフィル、取得範囲の上限、安全性チェックを実装。
    - J-Quants クライアント（jquants_client）を用いた取得・保存フローに対応。
  - ETL / pipeline モジュール
    - ETLResult データクラス（処理結果の集計、品質チェック結果やエラーリストを保持）を実装し再エクスポート（etl.py）。
    - pipeline モジュールは差分更新、バックフィル、品質チェックの集約方針を定義（品質チェックは集計して呼び出し元で判断する設計）。
    - DuckDB を使用したテーブル存在チェックや最大日付取得などのユーティリティを実装。
  - 一部の機能は jquants_client や quality モジュールと連携する設計（外部クライアントによるデータ取得・保存を前提）。

- 研究（Research）ユーティリティ (src/kabusys/research)
  - factor_research モジュール
    - モメンタム、ボラティリティ（ATR 等）、バリュー（PER/ROE）等の定量ファクター計算関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の window 関数を活用した効率的な SQL 実装。データ不足時は None を返す設計。
    - 計算結果は (date, code) ベースの辞書リストを返す仕様。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数、統計サマリー（factor_summary）を実装。
    - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。結合・欠損値処理や ties を考慮したランクアルゴリズムを搭載。

- ロギングと設計方針
  - ルックアヘッドバイアス防止のため各モジュールは datetime.today()/date.today() を直接参照しない（target_date を引数として扱う）。
  - DuckDB を主要なオンディスクデータストアとして想定しており、書き込みは冪等化（DELETE→INSERT 等）を意識。
  - OpenAI API 呼び出しに対してはリトライ戦略や 5xx / レート制限の取り扱いを実装し、ハードフェイルを避けるフェイルセーフ設計。

Changed
- （初期リリースにつき無し）

Fixed
- （初期リリースにつき無し）

Deprecated
- （初期リリースにつき無し）

Removed
- （初期リリースにつき無し）

Security
- 環境変数から機密トークンを扱う設計のため、運用時は OS 環境変数や secretos 管理を推奨。
- .env 自動読み込みはデフォルトで有効だが、テスト環境等での明示的無効化フラグを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Known limitations
- OpenAI API キーが必須:
  - news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY（または api_key 引数）が未設定だと ValueError を送出します。CI/運用環境ではキーの注入を忘れないでください。
- 一部モジュールは外部クライアント実装（jquants_client、quality 等）に依存しており、それらの実装により動作が決まります。
- 一部のファイル・関数はスニペットが提供された段階の実装に基づくため、周辺のユーティリティやエッジケース処理は今後の微調整・拡充が想定されます（例: ETL パイプラインの継続実装や細かいエラーメッセージの整備）。
- DuckDB のバージョン差異（executemany の空リスト取り扱い等）を考慮した互換性処理を含むが、実運用環境では DuckDB バージョンの確認を推奨。

Upgrade / Migration notes
- 本リリースは初期公開バージョンです。アップデート時には Settings に追加される環境変数や DB スキーマ変更に注意してください。

作者注
- 本 CHANGELOG は提供されたソースコードから実装意図を推測して作成しています。実際のリリースノート作成時には、追加の文脈（設計ドキュメント、リリース日、変更差分）を反映してください。