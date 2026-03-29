CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリース日付はコードベースから推測した日付を使用しています。

Unreleased
----------

- なし

0.1.0 - 2026-03-29
------------------

Added
- 初回リリース。KabuSys: 日本株自動売買／リサーチ／データ基盤用ライブラリを追加。
  - パッケージ初期化:
    - kabusys.__version__ = "0.1.0"
    - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ 宣言に準拠）
- 環境設定・ロード機能（kabusys.config）を追加。
  - .env ファイルの自動ロード機能を実装（プロジェクトルートは `.git` または `pyproject.toml` で検出）。
  - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサーは次をサポート:
    - export KEY=val 形式
    - シングル／ダブルクォートとバックスラッシュエスケープ
    - インラインコメント（スペース前の '#' をコメントと判断）
  - 環境値検証ユーティリティ _require と Settings クラスを提供（J-Quants, kabu API, Slack, DB パス, env/log level 判定等）。
  - 環境変数の保護（読み込み時に既存 OS 環境変数を保護する仕組み）を実装。
- AI 関連（kabusys.ai）を追加。
  - news_nlp モジュール:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) の JSON Mode でバッチスコアリングして ai_scores テーブルへ保存。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST 相当）計算ユーティリティ calc_news_window を提供。
    - バッチサイズ制御、記事・文字数トリム、レスポンスの堅牢なバリデーションを実装。
    - リトライ（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフを実装。失敗時はフェイルセーフによりスキップして継続。
    - DuckDB 0.10 互換性（executemany が空リストを受け付けない点）を考慮した DB 書き込みロジック。
  - regime_detector モジュール:
    - ETF（1321）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を判定・保存。
    - マクロキーワードで raw_news をフィルタ、OpenAI を呼び出して macro_sentiment を算出（記事がない場合は LLM 呼び出しを行わない）。
    - API 呼び出しのリトライ、エラー時のフォールバック（macro_sentiment = 0.0）を実装。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。失敗時は ROLLBACK を試み上位へ例外を伝搬。
- データ基盤関連（kabusys.data）を追加。
  - calendar_management:
    - market_calendar を基にした営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、カレンダーの夜間更新ジョブ（calendar_update_job）を実装。
    - DB にデータが存在しない場合は曜日ベースでフォールバックする堅牢設計。
    - 更新処理は J-Quants クライアント経由で差分取得 → 保存（ON CONFLICT の想定）し、バックフィルと健全性チェックを行う。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー一覧などを格納）。
    - ETL パイプラインのヘルパー（最終取得日の算出、テーブル存在チェック等）を実装。バックフィル、品質チェックとの連携設計を反映。
- リサーチ関連（kabusys.research）を追加。
  - factor_research:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）および流動性指標を DuckDB SQL を用いて計算する関数群を実装（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の None の扱い、ログ出力、計算ウィンドウのバッファ設定などを記述。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman ρ）計算、rank、factor_summary（基本統計）を実装。
    - 外部依存を排した実装、ランク計算の同順位処理（平均ランク）や数値の丸めによる ties 対応等を盛り込む。
- 共通実装・設計上の注意点（全体）
  - DuckDB を主要なローカル分析 DB として利用する設計で SQL を多用。
  - すべての日時ロジックはルックアヘッドバイアス防止のため date/target_date ベースで動作し、date.today() や datetime.today() へ依存しない実装方針。
  - OpenAI 呼び出し部分はテスト容易性のため内部呼び出し関数を分離しており、ユニットテストで差し替え可能（unittest.mock.patch を想定）。
  - OpenAI SDK の APIError に対するステータスコード存在の違い（status_code の有無）に対応する堅牢なエラーハンドリングを実装。
  - ロギングを豊富に追加し、失敗や異常時に動作を継続するフェイルセーフ設計を採用。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Security
- 初版のため該当なし。

Known limitations / Notes
- OpenAI API キーは呼び出し時に引数で注入可能だが、未指定時は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出する。
- AI スコアの数値は ±1.0 にクリップされる仕様。
- DuckDB のバージョン差分（executemany の空リスト扱い等）に注意して実装しているが、実運用ではターゲット DuckDB バージョンでの検証を推奨。
- 現時点では PBR・配当利回り等は未実装（calc_value の注記参照）。
- calendar_update_job や ETL の J‑Quants クライアント部（jquants_client）は外部モジュールに依存するため、実際に API を使うには適切なクレデンシャルとクライアントの導入が必要。

貢献
- 初回リリースにつき、詳細な貢献履歴は追って追加予定。バグ報告・改善提案は Issue を通じて歓迎します。