Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog の仕様に従います。

フォーマット:
- 重大な変更はカテゴリ別に記載します（Added, Changed, Fixed, Removed, Security）。
- 各リリースはバージョンと日付を付与します。

Unreleased
----------

（現時点の開発中変更はありません）

[0.1.0] - 2026-04-03
-------------------

初回公開リリース。パッケージ名: kabusys（日本株自動売買システムの基盤ライブラリ）。
主要な機能実装と設計方針を含む大規模な初期実装。

Added
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。
  - サブパッケージ公開: data, research, ai, monitoring, strategy, execution（__all__ により意図的に公開）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: __file__ から親ディレクトリを辿り .git または pyproject.toml を基準にルートを決定。
  - .env の堅牢なパーサを実装（コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 自動読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - Settings クラスを追加し、必要な設定値（J-Quants トークン、Kabu API パスワード、LINE トークン、DB パスなど）をプロパティとして提供。
  - 環境値検証: KABUSYS_ENV / LOG_LEVEL の許容値チェック。
  - 各種運用フラグ（PID ファイル・kill flag・リソース閾値など）を Settings で提供。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール: raw_news をまとめて OpenAI (gpt-4o-mini) に投げ、銘柄別センチメント (ai_scores) を算出・書き込みする機能を実装。
    - 時間ウィンドウ計算（JST 前日15:00～当日08:30、UTC換算）を提供。
    - バッチ処理（最大20銘柄/リクエスト）、1銘柄あたり記事数・文字数上限によるトリムをサポート。
    - レスポンスの堅牢なバリデーション（JSON抽出、results 構造チェック、スコアクリップ）。
    - レート制限・ネットワーク・5xx に対する指数バックオフリトライを実装。
    - 部分成功時に既存スコアを保護するため、取得したコードのみ DELETE → INSERT で差し替え。
    - テスト容易性のため、API 呼び出し関数をパッチ可能（unittest.mock.patch 対応）。

  - regime_detector モジュール: 市場レジーム判定（bull/neutral/bear）を日次で計算し market_regime テーブルへ保存。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成。
    - マクロニュース抽出はキーワードフィルタ（日本・米国など）を使用し、LLM による macro_sentiment を取得。
    - API エラーやパース失敗時は安全側の fallback（macro_sentiment=0.0）で継続。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。

- データ基盤（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar テーブル）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の判定ユーティリティ。
    - DB 登録値を優先し、未登録日は曜日ベース（週末非営業）でフォールバックする一貫性設計。
    - calendar_update_job により J-Quants から差分取得 → 冪等保存を実行。
    - 健全性チェック（過剰未来日やバックフィル等）を実装。

  - pipeline / etl: ETL パイプライン基盤を実装。
    - 差分取得、jquants_client 経由の保存（idempotent に保存するための設計）をサポート。
    - 品質チェック（quality モジュール）との統合ポイントを用意。品質問題は収集して返却する設計。
    - ETLResult データクラスを提供（実行統計・品質問題・エラーの集約、辞書化ユーティリティ付き）。
    - DuckDB を前提にした実装（テーブル存在チェック、最大日付取得ユーティリティ等）。

- リサーチ（kabusys.research）
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算関数を実装。
    - calc_momentum: mom_1m/3m/6m、ma200 偏差などを計算（200 行未満は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比などを計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を算出。
    - DuckDB SQL とウィンドウ関数を活用した効率的実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（IC）を実装（欠損ある場合やサンプル数不足を考慮）。
    - rank / factor_summary: ランク付けと統計サマリー（count/mean/std/min/max/median）を提供。
  - いずれも本番発注 API を呼ばない設計（分析専用）。

- 実装上の運用・安全措置
  - ルックアヘッドバイアス回避: 各モジュールで datetime.today()/date.today() の直接参照を避け、target_date ベースで処理。
  - DB トランザクションとロールバック: データ書き込み失敗時にロールバックを試み、ロールバック失敗はログで通知。
  - DuckDB 互換性の考慮: executemany に空リストを渡さない保護（DuckDB 0.10 対応）。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの厳密なパースを行う。
  - API キーの注入（関数引数）をサポートし、テスト容易性を確保。

Changed
- 初回リリースのため履歴なし。

Fixed
- 初回リリースのため履歴なし。

Removed
- 初回リリースのため履歴なし。

Security
- 初回リリースのため特記事項なし。

Notes / Design Decisions
- 外部依存を最小化: 分析モジュールは pandas 等に依存せず標準ライブラリ + DuckDB で実装。
- フェイルセーフ: LLM/API エラー時は例外で止めず、可能な限り安全なデフォルト（スコア 0.0 等）にフォールバックする方針。
- テスト可能性: API 呼び出しポイントを差し替え可能にして単体テストを容易にしている。

今後の予定（例）
- ai モジュールのモデル選択やプロンプト最適化、スコアの校正・正規化処理の拡張。
- ETL の監視・再実行ロジック、異常時のアラート統合（LINE/Slack 等）。
- 取引戦略（strategy）・発注（execution）周りの実装強化とシミュレーション機能の追加。

---

注: 上記はリポジトリ内のソースコードから推測した初回リリースの変更履歴です。運用上の実際の日付やパッケージ公開履歴に応じて適宜更新してください。