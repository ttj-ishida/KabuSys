# Changelog

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」の形式に準拠しています。セマンティックバージョニングを使用します。

なお、記載はリポジトリ内のコード（主に src/kabusys 配下の初期ファイル）から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
### 追加
- 初期リリース: `kabusys` パッケージを追加。
  - パッケージ説明（モジュールのドキュメンテーション文字列より）: "KabuSys - 日本株自動売買システム"
  - バージョン定義: `__version__ = "0.1.0"`
  - パブリック API: `__all__ = ["data", "strategy", "execution", "monitoring"]` を公開
- パッケージ構成（スケルトン／スタブファイルを作成）
  - `src/kabusys/__init__.py`
  - サブパッケージ（空の初期化ファイルを含む）
    - `src/kabusys/data/__init__.py`
    - `src/kabusys/strategy/__init__.py`
    - `src/kabusys/execution/__init__.py`
    - `src/kabusys/monitoring/__init__.py`

### 備考
- サブパッケージは現時点ではプレースホルダ（実装は未追加）であり、今後それぞれにデータ管理、戦略ロジック、注文実行、監視・ロギング等の実装が追加される想定です。