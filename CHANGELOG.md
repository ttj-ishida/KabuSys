Keep a Changelog
=================

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠します。  

[保守上の注記]
- バージョン番号はパッケージの __version__ と同期しています（src/kabusys/__init__.py）。
- 本CHANGELOGはコードから機能や設計意図を推測して記載しています。実装以外の変更（ドキュメントや設定ファイル等）が別途ある可能性があります。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-31
--------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（__all__）

- 環境変数・設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml を起点）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env 行パーサー実装（export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント考慮）
  - 環境変数保護（既存 OS 環境変数を protected として上書き抑止）
  - Settings クラスでアプリケーション設定を提供（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境モード・ログレベル判定）
  - 妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）
  - 必須環境変数取得ヘルパー（未設定時は ValueError）

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメントスコア算出
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済）
    - 銘柄ごとに最新記事を集約（最大記事数・最大文字数でトリム）
    - バッチ送信（デフォルト 20 銘柄/チャンク）
    - リトライ・バックオフ戦略（429, ネットワーク断, タイムアウト, 5xx を対象）
    - レスポンスバリデーション（JSON 抽出、results リスト、code/score 検証、スコアクリップ）
    - DuckDB へ冪等書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）
    - ルックアヘッドバイアス回避設計（内部で date.today() を使用しない）
    - テスト容易性: _call_openai_api を patch で差し替え可能
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）
    - マクロニュース取得用キーワードセットを用いたタイトルフィルタリング
    - OpenAI 呼び出し（gpt-4o-mini, JSON mode）に対するリトライ・バックオフ実装
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、エラー時は ROLLBACK を試行
    - ルックアヘッドバイアス回避（prices_daily クエリは target_date 未満を使用）

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を利用した営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB にデータがない/未登録日のフォールバックは曜日ベース（週末を非営業日と判定）
    - 最大探索範囲やバックフィル、健全性チェックを備えた calendar_update_job（J-Quants からの差分取得 → 保存）
    - 市場カレンダー更新はバックフィル日数を取り込み API 側の訂正を吸収
  - ETL パイプライン（pipeline）
    - 差分取得・保存・品質チェックの ETL 流れを想定したインターフェース実装
    - ETLResult dataclass を提供（取得数、保存数、品質問題、エラー一覧、ユーティリティ）
    - DuckDB 存在チェック / 最大日付取得等のユーティリティ関数
    - デフォルトのバックフィル、calendar lookahead 等の設定を定義
    - 品質チェックは Fail-Fast とせず検出結果を集約して返す設計
  - etl モジュールは pipeline.ETLResult を再エクスポート

- 研究・分析モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）
    - calc_value: PER（price / EPS）、ROE（raw_financials より取得）
    - 全て DuckDB の prices_daily / raw_financials のみ参照（発注 API にはアクセスしない）
    - データ不足時の None 処理やログ出力
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を用いた単一クエリ実装）
    - calc_ic: スピアマンランク相関（ランク化して Pearson を計算）、有効レコードが少ない場合 None を返す
    - rank: 同順位は平均ランクを割り当てる実装（丸めて ties 検出）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーユーティリティ
  - 研究用ユーティリティとして data.stats.zscore_normalize を re-export 想定（__init__）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （該当なし）

Known limitations / Notes
- OpenAI API の利用には環境変数 OPENAI_API_KEY（または関数引数）が必須。未設定時は ValueError を発生させる実装になっています。
- news_nlp の出力フォーマットは厳密な JSON を期待するため、LLM の応答パースに失敗するケースはスキップしてフェイルセーフで進めます（部分的なデータ欠損を許容）。
- calc_value は現時点で PBR、配当利回りなどを未実装（注記あり）。
- 一部関数は jquants_client 等の外部モジュールに依存（コード中で import 参照あり）。そのクライアント実装・外部 API のスキーマに依存します。
- DuckDB のバージョン差異（例: executemany の空リスト取り扱い）に配慮した実装上のワークアラウンドがあります。運用時は DuckDB バージョン互換性に注意してください。
- 本リリースはコードの実装内容に基づく初期機能群の提供を目的としており、運用向けのドキュメント・テスト・CI 設定は別途整備が必要です。

Acknowledgements / Implementation notes
- OpenAI 呼び出しは JSON mode を利用して厳密な機械可読出力を期待しています（model: gpt-4o-mini, response_format={"type":"json_object"}）。
- LLM 呼び出しロジックはニュース NLP と regime_detector で明示的に分離しており、テストのため patch しやすい作りになっています。
- ルックアヘッドバイアス防止のため、target_date ベースでの過去データ参照（date < target_date など）を徹底しています。

--------------------

（注）この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノート作成時はコミットログや PR コメント、実際の変更差分を参照のうえ調整してください。