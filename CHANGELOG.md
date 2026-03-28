# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
各バージョンのエントリは後方互換性やリリースノート作成時の参考になります。

## [0.1.0] - 2026-03-28

初回公開リリース。

### 追加 (Added)
- 基本パッケージ構成を導入
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（パッケージ外観を確立）
  - バージョン情報: __version__ = "0.1.0"

- 設定管理 (src/kabusys/config.py)
  - Settings クラスを追加し、環境変数から各種設定を取得するプロパティを提供
    - J-Quants / kabu ステーション / Slack / データベースパス / システム環境（env, log_level）等
  - .env 自動読み込み機能を実装
    - プロジェクトルートは .git または pyproject.toml を起点に検出（CWD 非依存）
    - 読み込み優先順位: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
  - .env 行パーサの強化
    - export プレフィックス対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ対応、インラインコメント処理
    - クォート無しでの # コメント判定の細やかな扱い
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL など）を実装
  - 必須変数未設定時は明示的な ValueError を送出

- データ関連 (src/kabusys/data/)
  - calendar_management モジュールを追加
    - market_calendar に基づく営業日判定ユーティリティ群を提供
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーが存在しない場合は曜日ベースのフォールバックを適用
    - 夜間バッチ: calendar_update_job により J-Quants から差分取得して保存（バックフィル・健全性チェック付き）
    - DuckDB との互換性や検索上限日数（_MAX_SEARCH_DAYS）等の安全策を実装
  - ETL パイプライン基盤を追加 (pipeline.py)
    - 差分取得・保存・品質チェックを行う設計（ETLResult データクラスを導入）
    - デフォルトのバックフィル日数、カレンダー先読み、品質チェックの扱い方針を定義
    - ETLResult.to_dict で品質問題を辞書化して監査ログ等に利用可能
  - etl モジュールで ETLResult を再エクスポート（data.etl）

- 研究 (research) モジュール群
  - factor_research モジュールを追加
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（ma200_dev）を計算
    - calc_volatility: 20日 ATR, 相対ATR(atr_pct), 20日平均売買代金, 出来高比率を計算
    - calc_value: raw_financials から PER / ROE を算出（EPS が 0/欠損の場合は None）
    - DuckDB を用いた SQL + Python 実装（外部 API / 発注 API へはアクセスしない）
  - feature_exploration モジュールを追加
    - calc_forward_returns: 任意ホライズンの将来リターン（fwd_1d, fwd_5d, fwd_21d など）
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算
    - rank, factor_summary: ランク変換・基本統計量サマリーを標準ライブラリのみで実装
    - 実装は pandas 等に依存しないことで軽量性とテスト容易性を重視
  - research パッケージの __init__ で zscore_normalize（data.stats）などを公開

- AI / NLP (src/kabusys/ai/)
  - news_nlp モジュールを追加 (news のセンチメントスコア算出)
    - score_news: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し ai_scores テーブルへ書込
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST の仕様（UTC へ変換）
    - 銘柄ごとに記事を集約（最大記事数・文字数でトリム）、最大 20 銘柄/コールのバッチ処理
    - JSON Mode を用いたレスポンス検証と堅牢なパース処理（前後の余計なテキストを含む場合の復元ロジック含む）
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ
    - API 失敗時は該当チャンクをスキップ（フェイルセーフ）し、部分失敗でも既存スコアを保護するために書込みは取得済みコードのみで DELETE→INSERT を実施
  - regime_detector モジュールを追加（市場レジーム判定）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の regime_label（bull/neutral/bear）を決定
    - calc_ma200_ratio, マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、合成スコア計算、market_regime への冪等書込を実装
    - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - OpenAI 呼び出しはモジュール内で独立実装（モジュール間の結合を避ける設計）
  - ai パッケージの __init__ で score_news を公開

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- OpenAI レスポンスのパースで JSON モードでも前後に余計なテキストが混ざるケースを考慮して、外側の最初と最後の波括弧を抽出して復元するロジックを追加（news_nlp）
- .env パースの堅牢性向上（クォート内エスケープ、export プレフィックス、コメント処理など）

### 既知の注意点 / 設計上の制約 (Notes)
- 日付/時刻は基本的に timezone-naive な date/datetime を使用し、明示的な UTC 変換や JST の解釈箇所をコメントで明記している（誤用に注意）
- DuckDB を主要なランタイム依存にしており、DuckDB のバージョン差異（配列バインド等）に配慮した実装（executemany の空リスト回避など）をしている
- OpenAI API キーは api_key 引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError を送出する
- 外部への書き込み（発注等）は本リリースでは実装しておらず、研究・データ取得・評価に焦点を当てている
- JSON パース失敗や API エラーはフェイルセーフ（スコアを 0 にする、あるいはチャンクをスキップ）で継続する設計

### セキュリティ (Security)
- OS 環境変数を保護するため .env の読み込み時に既存の OS 環境変数を上書きしない実装（ただし .env.local は override=True として上書き可能）
- 機密情報（API キー等）は環境変数で管理することを想定

---

今後の予定（例）
- strategy / execution / monitoring の具体実装（自動売買ロジック・約定管理・監視通知）
- より厳密な時刻管理（タイムゾーン対応）やテストカバレッジ拡充
- モデル選択やプロンプト改善、LLM 出力の堅牢化の継続的改善

（この CHANGELOG はコードベースの現状から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。）