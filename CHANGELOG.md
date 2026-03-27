Changelog
=========
すべての重要な変更はこのファイルに記録します。

フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。
<!--
  この CHANGELOG はコードベースから推測して自動作成されています。
  実際のリリースノートとして利用する場合は、必要に応じて追記・修正してください。
-->

未リリース
---------
（なし）

[0.1.0] - 2026-03-27
-------------------

Added
- 基本パッケージ初期実装
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開用 __all__ と __version__ を定義。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込み。プロジェクトルート判定は .git または pyproject.toml を探索して行うため、CWD に依存しない。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理を含む）。
  - .env 読み込み時の上書き制御（override）と OS 環境変数の保護（protected set）に対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境（KABUSYS_ENV）/ログレベルの取得とバリデーションを行う。KABUSYS_ENV は development/paper_trading/live を受け付け、LOG_LEVEL は標準レベルを検証。
- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュースセンチメント分類 (news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信するバッチ処理を実装。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供（UTC 変換済みで DB 比較に使用）。
    - バッチサイズ、1銘柄あたりの最大記事数および文字数上限（トークン肥大化対策）を実装。
    - JSON Mode を使った厳密なレスポンス検証、部分失敗を想定したフェイルセーフ挙動（失敗時は該当チャンクをスキップして継続）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。
    - DuckDB へは部分置換（DELETE → INSERT）で冪等に書き込む実装（空パラメータに対する互換性対応あり）。
    - テスト容易性のため、API 呼び出し内部関数はモック差し替え可能に設計。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF（1321）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次で判定し、market_regime テーブルへ冪等書き込み。
    - MA200 乖離は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除（datetime.today() を参照しない設計）。
    - マクロニュースは定義済みキーワードでフィルタし、OpenAI（gpt-4o-mini）へ投げて JSON レスポンスから score を抽出。API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - リトライ・エラーハンドリング（RateLimit, 接続エラー, タイムアウト, APIError の 5xx 判定）を実装。
- データ基盤関連 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダーを管理する market_calendar テーブル操作ユーティリティ（営業日判定、前後の営業日取得、期間内営業日取得、SQ日判定）。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする一貫したロジックを実装。
    - カレンダー更新バッチ calendar_update_job を提供（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスにより ETL 実行結果を集約（取得件数・保存件数・品質チェック結果・エラー等を格納）。
    - 差分更新、backfill、品質チェックの概念を導入（品質問題は収集して呼び出し元に委ねる設計）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。
  - jquants_client と連携する設計（fetch/save を利用する想定）。
- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility: 20 日 ATR（単純平均）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER, ROE（raw_financials から target_date 以前の最新財務データを結合）。
    - DuckDB を用いた SQL ベースの高速集計を実装。データ不足時は None を返す方針。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）に対応し、効率的な LEAD/LAG 集計で取得。
    - IC（calc_ic）計算：スピアマンのランク相関（ties は平均ランク）を実装。3 件未満は None を返す。
    - rank と factor_summary：同順位処理、統計サマリー（count/mean/std/min/max/median）を実装。
  - research パッケージ外からのユーティリティ再エクスポート（zscore_normalize 等）。
- ロギング・設計上の注意点
  - 主要処理はログ出力を多用し、警告や情報ログでフェイルセーフやデータ不足を通知。
  - ルックアヘッドバイアス回避のため、日付参照を関数引数ベースに統一（datetime.today()/date.today() の直接参照を避ける設計方針を徹底）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- 環境変数ロードで OS 側の既存環境変数を保護する仕組みを導入（.env 読み込み時に protected set を使用して重要な環境変数を上書きしない）。
- Settings で必須環境変数が未設定の場合に ValueError を発生させ、明示的に扱うように設計。

Notes / Implementation details（補足）
- OpenAI 呼び出しは現時点で gpt-4o-mini を想定し、JSON mode（response_format={"type":"json_object"}）での利用を前提としている。レスポンスのパース失敗や API 停止時には安全にフォールバックする実装になっている。
- DuckDB を DB 層として利用する想定。executemany に空リストを渡せないバージョン対応など、実環境での互換性を考慮した実装が散見される。
- テストしやすさを意識して内部の API 呼び出し関数（例: _call_openai_api）はモック可能にしている。
- JSON レスポンスの前後に余計なテキストが混入するケースに備え、最外の {} を抽出して復元を試みる耐性がある。

今後の改善案（提案）
- OpenAI クライアント生成箇所の抽象化（DI）を進めてテストやモデル切替を容易にする。
- ai モジュールのレスポンス検証をさらに厳密化し、不確実なスコアに対するメタ情報（confidence 等）を取り扱う。
- ETL のスケジューリング / 監視用の軽量 CLI やジョブ管理を追加する。

--- 

（この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートとして用いる場合は、コミット履歴・Issue・実際の変更差分に基づく最終確認を行ってください。）