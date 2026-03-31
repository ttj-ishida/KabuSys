CHANGELOG
=========

すべての注目すべき変更を記載します。本プロジェクトは Keep a Changelog の方針に従っており、セマンティックバージョニングを採用しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要時に記載

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース。
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - パッケージ公開用の __all__ を設定（data, strategy, execution, monitoring）。
- 環境設定管理モジュール（kabusys.config）を追加。
  - .env / .env.local ファイルおよび OS 環境変数から設定値を読み込む自動ロード機構を実装。
  - プロジェクトルートの検出は .git または pyproject.toml を基準に探索し、CWD に依存しない実装。
  - .env の行パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォートとエスケープ対応、インラインコメント処理）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - OS 環境変数を保護する protected 機構を実装（.env.local は既存 OS 環境変数を上書きしない）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / データベースパス / 動作環境（development, paper_trading, live）などをプロパティ経由で取得。
  - 必須環境変数未設定時には明確な ValueError を送出。
- AI 関連モジュール（kabusys.ai）を追加。
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を取得。
    - リトライ（429 / 接続断 / タイムアウト / 5xx）および指数バックオフを実装。
    - JSON Mode 出力のパースと復元ロジック（前後ノイズが混入した場合に外側の {} を取り出す等）。
    - スコアのバリデーション（型、既知コードチェック、数値・有限値チェック）、±1.0 でクリップ。
    - DuckDB との互換性を考慮し、部分失敗時に既存スコアを保護する「DELETE → INSERT」の冪等書き込み。
    - ニュース対象ウィンドウは JST を基準に定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して DB と比較）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの MA200 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュース抽出はキーワードベースでフィルタし、OpenAI を呼び出して JSON 出力から macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
- 研究（research）モジュールを追加（kabusys.research）。
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）計算を実装。
    - DuckDB の SQL を活用して効率的に計算し、結果は (date, code) キーの dict リストで返却。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク変換、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
- データ関連モジュールを追加（kabusys.data）。
  - calendar_management:
    - JPX カレンダー管理（market_calendar）の取得・更新ロジック、営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする一貫した動作。
    - calendar_update_job で J-Quants API から差分取得・バックフィル・健全性チェックを行い、取得結果を保存。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - 差分取得、保存（jquants_client 経由で冪等保存）、品質チェック（quality モジュールとの連携）を行う ETL の設計方針とユーティリティを実装。
    - DuckDB の存在確認、テーブル最大日付取得ユーティリティなどを用意。
- パッケージの __all__ エクスポートを適切に設定（ai, research などで公開 API を定義）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / 設計上の重要点
- ルックアヘッドバイアス防止:
  - 全ての AI / 研究 / ETL 関数は内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - prices_daily 等のクエリでは target_date 未満のみを参照する等、将来データ参照を回避。
- フェイルセーフと堅牢性:
  - OpenAI 呼び出しはネットワーク系や 5xx に対してリトライを実施し、最終的に失敗しても該当処理（macro_sentiment や chunk）をスキップして全体を継続するよう設計。
  - JSON のパースやレスポンスフォーマットの不備に対してログを残してスキップすることで処理の停滞を防止。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョンへの対応（呼び出し前に空チェックを行う）。
  - 日付値取り扱いで DuckDB が返す型を date に変換するユーティリティを提供。
- テストしやすさ:
  - OpenAI への実際の API 呼び出し箇所はモック差し替え可能な関数でラップ（unittest.mock.patch で置換可能）。
- 環境変数の取り扱い:
  - 必須キーが未設定の場合は ValueError で早期に明示。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑制、.env.local による開発上書き（ただし OS 環境変数は保護）など。

Security
- Slack トークン・OpenAI API キー等の機密情報は環境変数での管理を想定。設定を忘れた場合は例外で分かりやすく通知する設計。

既知の制約
- jquants_client, quality モジュールや外部 API の実装（実際の API クレデンシャル）は本リリースには含まれないため、実行環境側でそれらを用意する必要があります。
- 一部のテーブル（market_calendar, prices_daily, raw_news, news_symbols, raw_financials, ai_scores, market_regime 等）が前提であり、初期スキーマ作成は別途行う必要があります。

今後の予定（候補）
- Strategy / execution / monitoring の具体実装と統合テスト
- モデル（LLM）応答のより厳格なフォーマット検証・リカバリ手法の強化
- ETL の並列化とパフォーマンス最適化
- 監査ログおよびメトリクス出力の追加

--- 

（この CHANGELOG はコードの実装内容から推測して作成しています。実際のリリースノート作成時はテスト結果やデプロイ手順、マイグレーション情報などを追記してください。）