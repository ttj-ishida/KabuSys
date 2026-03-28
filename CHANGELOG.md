# Changelog

すべての注目すべき変更点を記録します。これは Keep a Changelog の形式に準拠しています。

既知の変更点のみをコードベースから推測して記載しています（実装・設計意図を含む）。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム "KabuSys" の基本機能群を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化 (src/kabusys/__init__.py) とバージョン定義 (__version__ = "0.1.0") を追加。
  - パブリックモジュールのエクスポート: data, strategy, execution, monitoring。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml）。
  - .env と .env.local の読み込み優先順位をサポート（.env.local が上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
  - .env パーサーの実装: export 形式、クォート内エスケープ、インラインコメントの処理等に対応。
  - 必須環境変数検証ヘルパー _require と Settings クラスを提供。J-Quants, kabu API, Slack, DB パス、実行環境（development/paper_trading/live）、ログレベル検証などのプロパティを実装。
  - デフォルトのデータベースパス（DuckDB/SQLite）設定を提供。

- AI（自然言語処理） (src/kabusys/ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価。
    - バッチ処理（最大20銘柄/チャンク）、記事数・文字数トリム、レスポンスバリデーション、スコア ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ処理を実装。致命的でない場合はスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは部分失敗に対して既存スコアを保護する方式（対象コードを限定して DELETE → INSERT）を採用。
    - テスト容易性を考慮して _call_openai_api を差し替え可能に実装。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して market_regime を算出／保存。
    - マクロ記事抽出（キーワードフィルタ） → OpenAI による macro_sentiment 評価 → スコア合成 → 冪等的に market_regime テーブルへ書き込み。
    - API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。OpenAI 呼び出し関数は news_nlp と独立した実装。
    - ルックアヘッドバイアス回避設計（target_date 未満のデータのみ参照、date.today() を直接参照しない）。

- データ処理 (src/kabusys/data)
  - マーケットカレンダー管理 (calendar_management.py)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などの営業日判定ユーティリティを実装。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（平日を営業日扱い）。
    - calendar_update_job を実装: J-Quants API から差分取得して market_calendar を冪等に更新、バックフィル・健全性チェックをサポート。
    - DB 未登録日の扱い・NULL 値の警告ログ出力など頑健な挙動を設計。

  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラーメッセージ等を集約）。
    - 差分更新・バックフィル・品質チェックを行う ETL 設計方針を反映（jquants_client / quality を利用する想定）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。

  - jquants_client のラッパー等（モジュール参照）を用いたデータ取得／保存フローを想定している旨の注釈を追加。

- リサーチ（研究）モジュール (src/kabusys/research)
  - factor_research: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等。
    - Value: PER（EPS が 0 / NULL の場合は None）、ROE（直近報告）。
    - DuckDB SQL + Python による実装で、本番口座や発注 API へはアクセスしない設計。
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装。
    - 将来リターン計算（任意ホライズン、最大 252 営業日制限、まとめて取得）。
    - IC（スピアマンのランク相関）計算、欠損・少数レコード時の扱い。
    - 統計サマリー（count/mean/std/min/max/median）とランク関数（同順位は平均ランク）を提供。
  - data.stats の zscore_normalize を再エクスポート。

### 変更 (Changed)
- （初版のため履歴はありませんが、設計ノートとして以下を明記）
  - 設計方針の明確化（ルックアヘッドバイアス防止、API エラー時のフェイルセーフ、部分失敗時の DB 保護 等）。

### 修正 (Fixed)
- （初版リリースのため過去の修正履歴はなし）

### 注記 / 設計上の重要点
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON mode を使用して厳密な JSON レスポンスを期待する実装。レスポンスパース失敗時は回避ロジック（{} の切り出し等）を含む。
- API リトライは 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフで再試行。その他のエラーはスキップして継続する（システムの可用性優先）。
- スコアは常にクリップ（ニュース: ±1.0、レジーム: ±1.0）して不正値混入を防止。
- DuckDB への書き込みは可能な限り冪等に実装（DELETE → INSERT、ON CONFLICT を想定）。また DuckDB の executemany に関する制約（空リスト不可）に対するワークアラウンドを実装。
- 単体テスト容易性のため、OpenAI 呼び出し部分はモック差し替えしやすい構造になっている（内部関数を patch 可能）。
- 環境変数周りは堅牢に設計されており、必須値がない場合は明確な ValueError を発生させる。

---

作成した CHANGELOG はコードの内容と設計コメントから推測してまとめたものであり、実際のコミット履歴とは差異がある可能性があります。必要であれば、コミットログやリリースノートに合わせて項目を調整できます。